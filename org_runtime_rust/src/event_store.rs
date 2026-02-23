//! Append-only event store — binary protobuf log.
//!
//! Storage format: length-prefixed protobuf frames.
//!   [4-byte LE length][protobuf bytes][4-byte LE length][protobuf bytes]...
//!
//! Rules:
//!   - Strict append only — no mutation, no deletion, no reordering
//!   - fsync after every write
//!   - Sequence strictly increasing (validated on append)
//!   - Events with schema_version != 1 are rejected by the kernel

use std::fs::{File, OpenOptions};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};

use prost::Message;

use crate::proto_types::ProtoEventEnvelope;

/// Append-only event log backed by a binary file.
pub struct EventStore {
    path: PathBuf,
    last_sequence: u64,
}

impl EventStore {
    /// Open or create an event log at the given path.
    /// Reads existing events to determine the last sequence number.
    pub fn open(path: &Path) -> io::Result<Self> {
        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        // Read existing events to determine last sequence
        let last_sequence = if path.exists() {
            let events = Self::read_all_from_file(path)?;
            events.last().map(|e| e.sequence).unwrap_or(0)
        } else {
            0
        };

        Ok(Self {
            path: path.to_path_buf(),
            last_sequence,
        })
    }

    /// Append a single event to the log.
    ///
    /// Validates strict sequence ordering.
    /// Writes length-prefixed protobuf and fsyncs.
    pub fn append_event(&mut self, event: &ProtoEventEnvelope) -> io::Result<()> {
        let expected = self.last_sequence + 1;
        if event.sequence != expected {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                format!(
                    "Sequence violation in event store: expected {}, got {}",
                    expected, event.sequence
                ),
            ));
        }

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)?;

        let buf = event.encode_to_vec();
        let len = buf.len() as u32;

        {
            let mut writer = BufWriter::new(&mut file);
            writer.write_all(&len.to_le_bytes())?;
            writer.write_all(&buf)?;
            writer.flush()?;
        }
        file.sync_all()?;

        self.last_sequence = event.sequence;
        Ok(())
    }

    /// Load all events from the log in sequence order.
    pub fn load_all_events(&self) -> io::Result<Vec<ProtoEventEnvelope>> {
        if !self.path.exists() {
            return Ok(Vec::new());
        }
        Self::read_all_from_file(&self.path)
    }

    /// Get the last sequence number in the log.
    pub fn last_sequence(&self) -> u64 {
        self.last_sequence
    }

    /// Read all events from a file, validating frame integrity.
    fn read_all_from_file(path: &Path) -> io::Result<Vec<ProtoEventEnvelope>> {
        let file = File::open(path)?;
        let mut reader = BufReader::new(file);
        let mut events = Vec::new();
        let mut len_buf = [0u8; 4];

        loop {
            match reader.read_exact(&mut len_buf) {
                Ok(()) => {}
                Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => break,
                Err(e) => return Err(e),
            }

            let len = u32::from_le_bytes(len_buf) as usize;
            if len == 0 || len > 16 * 1024 * 1024 {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("Invalid frame length: {}", len),
                ));
            }

            let mut frame = vec![0u8; len];
            reader.read_exact(&mut frame).map_err(|e| {
                io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("Truncated frame at offset: {}", e),
                )
            })?;

            let event = ProtoEventEnvelope::decode(frame.as_slice()).map_err(|e| {
                io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("Protobuf decode error: {}", e),
                )
            })?;

            events.push(event);
        }

        Ok(events)
    }
}
