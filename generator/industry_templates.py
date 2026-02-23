"""
Industry Templates — Domain-realistic organization blueprints.

Each industry × stage combination defines:
  - Departments with realistic names and varying sizes
  - Roles with real titles, purposes, and responsibilities
  - Natural dependency patterns (who depends on whom)

The compiler picks from these templates based on the user's selection,
then slices/scales by the success_level to control how many get emitted.

All data here is plain Python — no external deps.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class RoleBlueprint:
    """A realistic role definition."""
    id_suffix: str              # e.g. "eng_lead" → becomes "eng_lead"
    name: str                   # e.g. "Engineering Lead"
    purpose: str
    responsibilities: List[str]
    produced_outputs: List[str]
    required_inputs: List[str]


@dataclass
class DeptBlueprint:
    """A realistic department with its roles."""
    name: str                   # e.g. "Engineering"
    roles: List[RoleBlueprint]


@dataclass
class DependencyBlueprint:
    """A natural dependency between two roles."""
    from_role: str              # id_suffix of source role
    to_role: str                # id_suffix of target role
    dep_type: str               # "operational" | "informational" | "governance"
    critical: bool


@dataclass
class IndustryTemplate:
    """Complete org blueprint for an industry × stage."""
    industry: str
    stage: str
    departments: List[DeptBlueprint]
    dependencies: List[DependencyBlueprint]


# ═══════════════════════════════════════════════════════════════════════
# TECH SAAS
# ═══════════════════════════════════════════════════════════════════════

_TECH_SAAS_SEED = IndustryTemplate(
    industry="tech_saas",
    stage="seed",
    departments=[
        DeptBlueprint("Product & Engineering", [
            RoleBlueprint("cto", "CTO / Tech Lead", "Technical vision and architecture",
                          ["system_design", "code_review", "tech_strategy"],
                          ["architecture_docs", "technical_decisions"], ["product_requirements"]),
            RoleBlueprint("fullstack_1", "Full-Stack Developer", "Core product development",
                          ["feature_development", "bug_fixes", "deployment"],
                          ["shipped_features", "code_commits"], ["architecture_docs", "design_specs"]),
            RoleBlueprint("fullstack_2", "Full-Stack Developer II", "Product feature delivery",
                          ["feature_development", "testing", "api_design"],
                          ["shipped_features", "api_endpoints"], ["architecture_docs"]),
        ]),
        DeptBlueprint("Business & Growth", [
            RoleBlueprint("ceo", "CEO / Founder", "Company vision and fundraising",
                          ["fundraising", "strategy", "hiring", "customer_discovery"],
                          ["company_strategy", "funding"], ["market_data", "financial_reports"]),
            RoleBlueprint("growth_lead", "Growth Lead", "User acquisition and retention",
                          ["marketing", "analytics", "outreach"],
                          ["growth_metrics", "campaigns"], ["product_updates", "company_strategy"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("ceo", "cto", "governance", True),
        DependencyBlueprint("cto", "fullstack_1", "operational", True),
        DependencyBlueprint("cto", "fullstack_2", "operational", False),
        DependencyBlueprint("growth_lead", "ceo", "informational", False),
        DependencyBlueprint("fullstack_1", "fullstack_2", "operational", False),
        DependencyBlueprint("growth_lead", "fullstack_1", "informational", False),
    ],
)

_TECH_SAAS_GROWTH = IndustryTemplate(
    industry="tech_saas",
    stage="growth",
    departments=[
        DeptBlueprint("Engineering", [
            RoleBlueprint("vp_eng", "VP Engineering", "Engineering leadership and delivery",
                          ["team_management", "sprint_planning", "architecture_review"],
                          ["engineering_roadmap", "technical_decisions"], ["product_roadmap"]),
            RoleBlueprint("backend_lead", "Backend Lead", "API and infrastructure",
                          ["api_design", "database_management", "performance"],
                          ["api_services", "data_models"], ["engineering_roadmap"]),
            RoleBlueprint("frontend_lead", "Frontend Lead", "UI/UX implementation",
                          ["ui_development", "component_library", "accessibility"],
                          ["ui_components", "user_interfaces"], ["design_specs", "api_services"]),
            RoleBlueprint("devops", "DevOps Engineer", "CI/CD and infrastructure",
                          ["deployment", "monitoring", "cloud_infra"],
                          ["deployment_pipelines", "infra_configs"], ["api_services"]),
            RoleBlueprint("qa_lead", "QA Lead", "Quality assurance and testing",
                          ["test_strategy", "automation", "regression"],
                          ["test_reports", "quality_metrics"], ["ui_components", "api_services"]),
        ]),
        DeptBlueprint("Product", [
            RoleBlueprint("product_mgr", "Product Manager", "Product strategy and roadmap",
                          ["user_research", "feature_prioritization", "stakeholder_mgmt"],
                          ["product_roadmap", "feature_specs"], ["market_data", "user_feedback"]),
            RoleBlueprint("designer", "Product Designer", "UX/UI design",
                          ["user_flows", "wireframing", "design_system"],
                          ["design_specs", "prototypes"], ["feature_specs", "user_feedback"]),
        ]),
        DeptBlueprint("Sales & Marketing", [
            RoleBlueprint("sales_lead", "Sales Lead", "Revenue generation",
                          ["prospecting", "deal_closing", "pipeline_mgmt"],
                          ["revenue_reports", "deal_pipeline"], ["product_roadmap", "marketing_leads"]),
            RoleBlueprint("marketing_mgr", "Marketing Manager", "Brand and demand generation",
                          ["content_strategy", "campaigns", "analytics"],
                          ["marketing_leads", "brand_assets"], ["product_roadmap"]),
        ]),
        DeptBlueprint("Operations", [
            RoleBlueprint("ops_mgr", "Operations Manager", "Business operations",
                          ["process_optimization", "vendor_mgmt", "compliance"],
                          ["operational_reports", "process_docs"], ["financial_reports"]),
            RoleBlueprint("support_lead", "Customer Support Lead", "Customer success",
                          ["ticket_management", "escalation", "knowledge_base"],
                          ["support_metrics", "user_feedback"], ["product_roadmap", "shipped_features"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("vp_eng", "product_mgr", "operational", True),
        DependencyBlueprint("product_mgr", "designer", "operational", True),
        DependencyBlueprint("designer", "frontend_lead", "operational", True),
        DependencyBlueprint("vp_eng", "backend_lead", "operational", True),
        DependencyBlueprint("vp_eng", "frontend_lead", "governance", False),
        DependencyBlueprint("backend_lead", "devops", "operational", True),
        DependencyBlueprint("frontend_lead", "qa_lead", "operational", False),
        DependencyBlueprint("backend_lead", "qa_lead", "operational", False),
        DependencyBlueprint("sales_lead", "marketing_mgr", "operational", False),
        DependencyBlueprint("marketing_mgr", "product_mgr", "informational", False),
        DependencyBlueprint("support_lead", "product_mgr", "informational", False),
        DependencyBlueprint("support_lead", "qa_lead", "informational", False),
        DependencyBlueprint("ops_mgr", "vp_eng", "governance", False),
        DependencyBlueprint("sales_lead", "product_mgr", "informational", False),
    ],
)

_TECH_SAAS_STRUCTURED = IndustryTemplate(
    industry="tech_saas",
    stage="structured",
    departments=[
        DeptBlueprint("Platform Engineering", [
            RoleBlueprint("vp_eng", "VP Engineering", "Engineering org leadership",
                          ["team_management", "technical_strategy", "hiring"],
                          ["engineering_roadmap"], ["company_strategy"]),
            RoleBlueprint("backend_sr", "Senior Backend Engineer", "Core services",
                          ["microservices", "api_design", "database_optimization"],
                          ["api_services", "data_models"], ["engineering_roadmap"]),
            RoleBlueprint("backend_jr", "Backend Engineer", "Feature development",
                          ["feature_implementation", "testing", "documentation"],
                          ["code_commits"], ["api_services", "data_models"]),
            RoleBlueprint("infra_lead", "Infrastructure Lead", "Cloud and scaling",
                          ["cloud_architecture", "cost_optimization", "disaster_recovery"],
                          ["infra_configs", "deployment_pipelines"], ["api_services"]),
            RoleBlueprint("sre", "Site Reliability Engineer", "System reliability",
                          ["monitoring", "incident_response", "capacity_planning"],
                          ["uptime_reports", "incident_postmortems"], ["infra_configs"]),
        ]),
        DeptBlueprint("Frontend & Design", [
            RoleBlueprint("frontend_lead", "Frontend Lead", "Client-side architecture",
                          ["react_architecture", "performance", "component_library"],
                          ["ui_components"], ["design_specs", "api_services"]),
            RoleBlueprint("frontend_dev", "Frontend Developer", "UI feature delivery",
                          ["feature_development", "responsive_design", "testing"],
                          ["shipped_features"], ["ui_components", "design_specs"]),
            RoleBlueprint("ux_designer", "UX Designer", "User experience",
                          ["user_research", "wireframing", "usability_testing"],
                          ["design_specs", "prototypes"], ["product_requirements"]),
            RoleBlueprint("ui_designer", "UI Designer", "Visual design",
                          ["visual_design", "design_system", "branding"],
                          ["visual_assets", "style_guides"], ["prototypes"]),
        ]),
        DeptBlueprint("Product Management", [
            RoleBlueprint("head_product", "Head of Product", "Product vision",
                          ["product_strategy", "okr_setting", "stakeholder_alignment"],
                          ["product_roadmap", "product_requirements"], ["company_strategy", "market_data"]),
            RoleBlueprint("pm_growth", "PM Growth", "Growth features",
                          ["a_b_testing", "funnel_optimization", "feature_specs"],
                          ["growth_specs", "experiment_results"], ["product_roadmap", "analytics_data"]),
            RoleBlueprint("pm_platform", "PM Platform", "Platform features",
                          ["api_strategy", "developer_experience", "feature_specs"],
                          ["platform_specs"], ["product_roadmap", "api_services"]),
        ]),
        DeptBlueprint("Revenue", [
            RoleBlueprint("sales_dir", "Sales Director", "Revenue strategy",
                          ["team_leadership", "enterprise_deals", "forecasting"],
                          ["revenue_reports", "sales_forecasts"], ["product_roadmap"]),
            RoleBlueprint("ae_1", "Account Executive", "Deal closing",
                          ["prospecting", "demos", "negotiations"],
                          ["deal_pipeline"], ["sales_forecasts", "marketing_leads"]),
            RoleBlueprint("csm", "Customer Success Manager", "Retention and expansion",
                          ["onboarding", "health_monitoring", "upselling"],
                          ["customer_health_scores", "user_feedback"], ["shipped_features"]),
        ]),
        DeptBlueprint("People & Finance", [
            RoleBlueprint("hr_mgr", "HR Manager", "People operations",
                          ["recruiting", "culture", "performance_reviews"],
                          ["headcount_plans", "culture_reports"], ["company_strategy"]),
            RoleBlueprint("finance_mgr", "Finance Manager", "Financial planning",
                          ["budgeting", "reporting", "compliance"],
                          ["financial_reports", "budget_plans"], ["revenue_reports"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("vp_eng", "head_product", "operational", True),
        DependencyBlueprint("head_product", "pm_growth", "governance", True),
        DependencyBlueprint("head_product", "pm_platform", "governance", True),
        DependencyBlueprint("pm_growth", "frontend_lead", "operational", False),
        DependencyBlueprint("pm_platform", "backend_sr", "operational", True),
        DependencyBlueprint("backend_sr", "backend_jr", "operational", False),
        DependencyBlueprint("backend_sr", "infra_lead", "operational", False),
        DependencyBlueprint("infra_lead", "sre", "operational", True),
        DependencyBlueprint("ux_designer", "frontend_lead", "operational", True),
        DependencyBlueprint("ui_designer", "ux_designer", "operational", False),
        DependencyBlueprint("frontend_lead", "frontend_dev", "operational", False),
        DependencyBlueprint("sales_dir", "ae_1", "governance", True),
        DependencyBlueprint("csm", "head_product", "informational", False),
        DependencyBlueprint("csm", "pm_growth", "informational", False),
        DependencyBlueprint("sales_dir", "head_product", "informational", False),
        DependencyBlueprint("hr_mgr", "vp_eng", "informational", False),
        DependencyBlueprint("finance_mgr", "sales_dir", "informational", False),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# MANUFACTURING
# ═══════════════════════════════════════════════════════════════════════

_MANUFACTURING_SEED = IndustryTemplate(
    industry="manufacturing",
    stage="seed",
    departments=[
        DeptBlueprint("Production", [
            RoleBlueprint("prod_mgr", "Production Manager", "Oversee manufacturing output",
                          ["scheduling", "quality_control", "safety_compliance"],
                          ["production_schedule", "quality_reports"], ["raw_material_orders"]),
            RoleBlueprint("operator_1", "Machine Operator", "Equipment operation",
                          ["machine_operation", "maintenance", "defect_reporting"],
                          ["finished_parts"], ["production_schedule"]),
            RoleBlueprint("operator_2", "Machine Operator II", "Secondary line operation",
                          ["machine_operation", "assembly", "inventory_tracking"],
                          ["assembled_units"], ["production_schedule", "finished_parts"]),
        ]),
        DeptBlueprint("Supply & Admin", [
            RoleBlueprint("owner", "Owner / GM", "Business direction and procurement",
                          ["vendor_relations", "financial_oversight", "hiring"],
                          ["company_strategy", "raw_material_orders"], ["financial_reports"]),
            RoleBlueprint("warehouse", "Warehouse Clerk", "Inventory and shipping",
                          ["receiving", "inventory_mgmt", "shipping"],
                          ["inventory_reports", "shipment_logs"], ["assembled_units", "raw_material_orders"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("owner", "prod_mgr", "governance", True),
        DependencyBlueprint("prod_mgr", "operator_1", "operational", True),
        DependencyBlueprint("prod_mgr", "operator_2", "operational", True),
        DependencyBlueprint("operator_1", "operator_2", "operational", False),
        DependencyBlueprint("warehouse", "prod_mgr", "informational", False),
        DependencyBlueprint("owner", "warehouse", "governance", False),
    ],
)

_MANUFACTURING_GROWTH = IndustryTemplate(
    industry="manufacturing",
    stage="growth",
    departments=[
        DeptBlueprint("Production Line A", [
            RoleBlueprint("line_mgr_a", "Line Manager A", "Primary production line",
                          ["shift_scheduling", "output_targets", "safety"],
                          ["line_a_output", "shift_reports"], ["production_plan"]),
            RoleBlueprint("sr_operator_a", "Senior Operator A", "Skilled machine work",
                          ["cnc_operation", "tooling", "junior_training"],
                          ["precision_parts"], ["shift_reports"]),
            RoleBlueprint("jr_operator_a", "Junior Operator A", "Assembly and support",
                          ["assembly", "cleaning", "basic_machining"],
                          ["assembled_goods"], ["precision_parts"]),
        ]),
        DeptBlueprint("Production Line B", [
            RoleBlueprint("line_mgr_b", "Line Manager B", "Secondary production line",
                          ["shift_scheduling", "quality_assurance", "maintenance"],
                          ["line_b_output", "quality_logs"], ["production_plan"]),
            RoleBlueprint("operator_b1", "Operator B1", "Finishing and packaging",
                          ["finishing", "packaging", "labeling"],
                          ["finished_products"], ["line_a_output"]),
        ]),
        DeptBlueprint("Quality & Compliance", [
            RoleBlueprint("qa_inspector", "QA Inspector", "Quality inspection",
                          ["incoming_inspection", "process_audit", "defect_tracking"],
                          ["quality_reports", "compliance_certs"], ["line_a_output", "line_b_output"]),
            RoleBlueprint("safety_officer", "Safety Officer", "Workplace safety",
                          ["safety_audits", "incident_investigation", "training"],
                          ["safety_reports"], ["shift_reports"]),
        ]),
        DeptBlueprint("Supply Chain & Admin", [
            RoleBlueprint("plant_dir", "Plant Director", "Overall operations",
                          ["strategic_planning", "budget_management", "customer_relations"],
                          ["production_plan", "company_strategy"], ["financial_reports", "quality_reports"]),
            RoleBlueprint("procurement", "Procurement Specialist", "Material sourcing",
                          ["vendor_management", "cost_negotiation", "order_tracking"],
                          ["purchase_orders", "raw_material_orders"], ["production_plan"]),
            RoleBlueprint("logistics", "Logistics Coordinator", "Shipping and distribution",
                          ["route_planning", "carrier_management", "tracking"],
                          ["shipment_schedules"], ["finished_products"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("plant_dir", "line_mgr_a", "governance", True),
        DependencyBlueprint("plant_dir", "line_mgr_b", "governance", True),
        DependencyBlueprint("line_mgr_a", "sr_operator_a", "operational", True),
        DependencyBlueprint("sr_operator_a", "jr_operator_a", "operational", False),
        DependencyBlueprint("line_mgr_b", "operator_b1", "operational", True),
        DependencyBlueprint("operator_b1", "sr_operator_a", "operational", False),
        DependencyBlueprint("qa_inspector", "line_mgr_a", "informational", True),
        DependencyBlueprint("qa_inspector", "line_mgr_b", "informational", True),
        DependencyBlueprint("safety_officer", "line_mgr_a", "governance", False),
        DependencyBlueprint("procurement", "plant_dir", "operational", False),
        DependencyBlueprint("logistics", "operator_b1", "operational", False),
        DependencyBlueprint("logistics", "procurement", "informational", False),
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# MARKETPLACE
# ═══════════════════════════════════════════════════════════════════════

_MARKETPLACE_SEED = IndustryTemplate(
    industry="marketplace",
    stage="seed",
    departments=[
        DeptBlueprint("Platform", [
            RoleBlueprint("tech_lead", "Tech Lead", "Platform architecture",
                          ["system_design", "development", "deployment"],
                          ["platform_code", "api_endpoints"], ["product_specs"]),
            RoleBlueprint("dev_1", "Developer", "Feature development",
                          ["feature_coding", "bug_fixes", "testing"],
                          ["shipped_features"], ["platform_code"]),
        ]),
        DeptBlueprint("Supply Side", [
            RoleBlueprint("supply_mgr", "Supply Manager", "Seller/provider onboarding",
                          ["seller_outreach", "onboarding", "quality_vetting"],
                          ["active_sellers", "supply_metrics"], ["platform_code"]),
        ]),
        DeptBlueprint("Demand & Growth", [
            RoleBlueprint("founder", "Founder / CEO", "Vision and growth",
                          ["strategy", "fundraising", "partnerships"],
                          ["company_strategy", "product_specs"], ["market_data"]),
            RoleBlueprint("community", "Community Manager", "User engagement",
                          ["content_creation", "social_media", "user_support"],
                          ["engagement_reports", "user_feedback"], ["company_strategy"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("founder", "tech_lead", "governance", True),
        DependencyBlueprint("tech_lead", "dev_1", "operational", True),
        DependencyBlueprint("founder", "supply_mgr", "governance", False),
        DependencyBlueprint("supply_mgr", "tech_lead", "operational", False),
        DependencyBlueprint("community", "founder", "informational", False),
        DependencyBlueprint("community", "supply_mgr", "informational", False),
    ],
)

_MARKETPLACE_GROWTH = IndustryTemplate(
    industry="marketplace",
    stage="growth",
    departments=[
        DeptBlueprint("Platform Engineering", [
            RoleBlueprint("eng_mgr", "Engineering Manager", "Technical team leadership",
                          ["sprint_planning", "architecture", "hiring"],
                          ["engineering_roadmap"], ["product_roadmap"]),
            RoleBlueprint("backend_dev", "Backend Developer", "API and matching logic",
                          ["matching_algorithm", "api_development", "data_pipeline"],
                          ["api_services", "matching_engine"], ["engineering_roadmap"]),
            RoleBlueprint("frontend_dev", "Frontend Developer", "Web/mobile interfaces",
                          ["ui_development", "responsive_design", "performance"],
                          ["user_interfaces"], ["api_services", "design_specs"]),
            RoleBlueprint("data_eng", "Data Engineer", "Analytics infrastructure",
                          ["etl_pipelines", "data_warehousing", "reporting"],
                          ["analytics_data", "dashboards"], ["api_services"]),
        ]),
        DeptBlueprint("Supply Operations", [
            RoleBlueprint("supply_dir", "Supply Director", "Supply-side strategy",
                          ["vendor_strategy", "quality_standards", "pricing"],
                          ["supply_strategy", "vendor_scorecards"], ["company_strategy"]),
            RoleBlueprint("supply_ops", "Supply Operations Specialist", "Day-to-day supply",
                          ["onboarding", "dispute_resolution", "performance_tracking"],
                          ["supply_metrics", "active_sellers"], ["supply_strategy"]),
        ]),
        DeptBlueprint("Demand & Marketing", [
            RoleBlueprint("marketing_dir", "Marketing Director", "Demand generation",
                          ["campaign_strategy", "brand_building", "budget_mgmt"],
                          ["marketing_plans", "campaign_reports"], ["product_roadmap"]),
            RoleBlueprint("growth_hacker", "Growth Hacker", "Viral and paid acquisition",
                          ["seo", "paid_ads", "referral_programs"],
                          ["traffic_reports", "marketing_leads"], ["marketing_plans"]),
            RoleBlueprint("content_mgr", "Content Manager", "Content and community",
                          ["editorial_calendar", "social_media", "partnerships"],
                          ["content_assets"], ["marketing_plans"]),
        ]),
        DeptBlueprint("Trust & Safety", [
            RoleBlueprint("trust_lead", "Trust & Safety Lead", "Platform integrity",
                          ["fraud_detection", "policy_enforcement", "user_verification"],
                          ["trust_reports", "policy_docs"], ["analytics_data"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("eng_mgr", "backend_dev", "operational", True),
        DependencyBlueprint("eng_mgr", "frontend_dev", "operational", True),
        DependencyBlueprint("eng_mgr", "data_eng", "operational", False),
        DependencyBlueprint("backend_dev", "frontend_dev", "operational", False),
        DependencyBlueprint("supply_dir", "supply_ops", "governance", True),
        DependencyBlueprint("supply_ops", "backend_dev", "operational", False),
        DependencyBlueprint("marketing_dir", "growth_hacker", "governance", True),
        DependencyBlueprint("marketing_dir", "content_mgr", "governance", False),
        DependencyBlueprint("trust_lead", "supply_ops", "governance", True),
        DependencyBlueprint("trust_lead", "data_eng", "operational", False),
        DependencyBlueprint("growth_hacker", "data_eng", "informational", False),
        DependencyBlueprint("content_mgr", "supply_dir", "informational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# TECH SAAS — MATURE
# ═══════════════════════════════════════════════════════════════════════

_TECH_SAAS_MATURE = IndustryTemplate(
    industry="tech_saas",
    stage="mature",
    departments=[
        DeptBlueprint("Core Platform Engineering", [
            RoleBlueprint("cto", "CTO", "Technical vision and architecture governance",
                          ["technical_strategy", "architecture_review", "vendor_evaluation"],
                          ["technical_roadmap", "architecture_decisions"], ["company_strategy"]),
            RoleBlueprint("vp_eng", "VP Engineering", "Engineering org leadership",
                          ["team_management", "hiring", "process_improvement"],
                          ["engineering_roadmap", "team_plans"], ["technical_roadmap"]),
            RoleBlueprint("backend_principal", "Principal Backend Engineer", "Core services architecture",
                          ["system_design", "code_review", "mentoring"],
                          ["api_services", "design_docs"], ["engineering_roadmap"]),
            RoleBlueprint("backend_sr", "Senior Backend Engineer", "Service implementation",
                          ["microservices", "database_optimization", "performance"],
                          ["data_models", "code_commits"], ["api_services"]),
            RoleBlueprint("backend_mid", "Backend Engineer", "Feature development",
                          ["feature_implementation", "testing", "documentation"],
                          ["feature_code"], ["data_models", "design_docs"]),
        ]),
        DeptBlueprint("Frontend & User Experience", [
            RoleBlueprint("frontend_lead", "Frontend Lead", "Client-side architecture",
                          ["react_architecture", "performance", "component_library"],
                          ["ui_components", "frontend_standards"], ["design_specs", "api_services"]),
            RoleBlueprint("frontend_sr", "Senior Frontend Engineer", "Complex UI features",
                          ["feature_development", "accessibility", "testing"],
                          ["shipped_features"], ["ui_components", "frontend_standards"]),
            RoleBlueprint("ux_lead", "UX Lead", "User experience strategy",
                          ["user_research", "design_system", "usability_testing"],
                          ["design_specs", "ux_reports"], ["product_requirements"]),
            RoleBlueprint("ui_designer", "UI Designer", "Visual design and branding",
                          ["visual_design", "iconography", "style_guides"],
                          ["visual_assets", "prototypes"], ["design_specs"]),
        ]),
        DeptBlueprint("Infrastructure & Reliability", [
            RoleBlueprint("infra_dir", "Director of Infrastructure", "Cloud strategy and operations",
                          ["cloud_architecture", "cost_optimization", "vendor_management"],
                          ["infra_roadmap", "infra_configs"], ["technical_roadmap"]),
            RoleBlueprint("sre_lead", "SRE Lead", "Site reliability and incident management",
                          ["monitoring", "incident_response", "capacity_planning"],
                          ["uptime_reports", "incident_postmortems"], ["infra_configs"]),
            RoleBlueprint("security_eng", "Security Engineer", "Application and infrastructure security",
                          ["security_audits", "vulnerability_management", "compliance"],
                          ["security_reports", "compliance_certs"], ["infra_configs", "api_services"]),
        ]),
        DeptBlueprint("Product Management", [
            RoleBlueprint("cpo", "Chief Product Officer", "Product vision and strategy",
                          ["product_strategy", "market_analysis", "stakeholder_alignment"],
                          ["product_roadmap", "product_requirements"], ["company_strategy"]),
            RoleBlueprint("pm_core", "PM Core Platform", "Core product features",
                          ["feature_specs", "user_stories", "sprint_planning"],
                          ["core_specs"], ["product_roadmap", "user_feedback"]),
            RoleBlueprint("pm_growth", "PM Growth", "Growth and acquisition features",
                          ["a_b_testing", "funnel_optimization", "experiment_design"],
                          ["growth_specs", "experiment_results"], ["product_roadmap", "analytics_data"]),
            RoleBlueprint("pm_enterprise", "PM Enterprise", "Enterprise features and integrations",
                          ["enterprise_requirements", "api_strategy", "partner_integrations"],
                          ["enterprise_specs"], ["product_roadmap"]),
        ]),
        DeptBlueprint("Revenue & Go-to-Market", [
            RoleBlueprint("cro", "Chief Revenue Officer", "Revenue strategy and forecasting",
                          ["revenue_strategy", "forecasting", "team_leadership"],
                          ["revenue_reports", "sales_forecasts"], ["product_roadmap"]),
            RoleBlueprint("sales_dir", "Sales Director", "Enterprise sales execution",
                          ["deal_management", "pipeline_review", "team_coaching"],
                          ["deal_pipeline"], ["sales_forecasts", "marketing_leads"]),
            RoleBlueprint("csm_lead", "Customer Success Lead", "Retention and expansion",
                          ["onboarding", "health_monitoring", "upselling"],
                          ["customer_health_scores", "user_feedback"], ["shipped_features"]),
            RoleBlueprint("marketing_dir", "Marketing Director", "Brand and demand generation",
                          ["campaign_strategy", "brand_building", "budget_management"],
                          ["marketing_plans", "marketing_leads"], ["product_roadmap"]),
        ]),
        DeptBlueprint("People & Operations", [
            RoleBlueprint("vp_people", "VP People", "People strategy and culture",
                          ["recruiting_strategy", "culture_programs", "compensation"],
                          ["headcount_plans", "culture_reports"], ["company_strategy"]),
            RoleBlueprint("finance_dir", "Finance Director", "Financial planning and reporting",
                          ["budgeting", "financial_modeling", "compliance"],
                          ["financial_reports", "budget_plans"], ["revenue_reports"]),
            RoleBlueprint("legal_counsel", "General Counsel", "Legal and regulatory compliance",
                          ["contract_review", "ip_protection", "regulatory_compliance"],
                          ["legal_opinions", "contract_templates"], ["company_strategy"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("cto", "vp_eng", "governance", True),
        DependencyBlueprint("cto", "infra_dir", "governance", True),
        DependencyBlueprint("vp_eng", "backend_principal", "operational", True),
        DependencyBlueprint("backend_principal", "backend_sr", "operational", True),
        DependencyBlueprint("backend_sr", "backend_mid", "operational", False),
        DependencyBlueprint("cpo", "pm_core", "governance", True),
        DependencyBlueprint("cpo", "pm_growth", "governance", True),
        DependencyBlueprint("cpo", "pm_enterprise", "governance", False),
        DependencyBlueprint("pm_core", "frontend_lead", "operational", False),
        DependencyBlueprint("pm_core", "backend_principal", "operational", False),
        DependencyBlueprint("frontend_lead", "frontend_sr", "operational", False),
        DependencyBlueprint("ux_lead", "frontend_lead", "operational", True),
        DependencyBlueprint("ui_designer", "ux_lead", "operational", False),
        DependencyBlueprint("infra_dir", "sre_lead", "operational", True),
        DependencyBlueprint("infra_dir", "security_eng", "operational", False),
        DependencyBlueprint("cro", "sales_dir", "governance", True),
        DependencyBlueprint("cro", "csm_lead", "governance", False),
        DependencyBlueprint("cro", "marketing_dir", "governance", False),
        DependencyBlueprint("csm_lead", "cpo", "informational", False),
        DependencyBlueprint("sales_dir", "pm_enterprise", "informational", False),
        DependencyBlueprint("vp_people", "vp_eng", "informational", False),
        DependencyBlueprint("finance_dir", "cro", "informational", False),
        DependencyBlueprint("pm_growth", "frontend_lead", "operational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# MANUFACTURING — STRUCTURED
# ═══════════════════════════════════════════════════════════════════════

_MANUFACTURING_STRUCTURED = IndustryTemplate(
    industry="manufacturing",
    stage="structured",
    departments=[
        DeptBlueprint("Production Operations", [
            RoleBlueprint("vp_ops", "VP Operations", "Manufacturing operations leadership",
                          ["capacity_planning", "lean_implementation", "budget_management"],
                          ["operations_roadmap", "production_plan"], ["company_strategy"]),
            RoleBlueprint("prod_mgr_a", "Production Manager A", "Primary line management",
                          ["shift_scheduling", "output_targets", "team_leadership"],
                          ["line_a_output", "shift_reports"], ["production_plan"]),
            RoleBlueprint("prod_mgr_b", "Production Manager B", "Secondary line management",
                          ["shift_scheduling", "quality_assurance", "maintenance_planning"],
                          ["line_b_output", "quality_logs"], ["production_plan"]),
            RoleBlueprint("sr_operator", "Senior Machine Operator", "Skilled machining and tooling",
                          ["cnc_operation", "tooling_setup", "junior_training"],
                          ["precision_parts"], ["shift_reports"]),
            RoleBlueprint("operator_1", "Machine Operator", "Production line operation",
                          ["machine_operation", "assembly", "defect_reporting"],
                          ["assembled_units"], ["precision_parts"]),
        ]),
        DeptBlueprint("Quality Assurance & Compliance", [
            RoleBlueprint("qa_mgr", "QA Manager", "Quality management system leadership",
                          ["quality_strategy", "audit_management", "certification_prep"],
                          ["quality_reports", "compliance_certs"], ["line_a_output", "line_b_output"]),
            RoleBlueprint("qa_inspector", "QA Inspector", "Incoming and in-process inspection",
                          ["inspection_protocols", "sampling_plans", "defect_analysis"],
                          ["inspection_reports"], ["quality_reports"]),
            RoleBlueprint("safety_officer", "EHS Officer", "Environment, health, and safety",
                          ["safety_audits", "incident_investigation", "regulatory_compliance"],
                          ["safety_reports", "ehs_records"], ["shift_reports"]),
        ]),
        DeptBlueprint("Engineering & Continuous Improvement", [
            RoleBlueprint("eng_mgr", "Engineering Manager", "Process and product engineering",
                          ["process_design", "tooling_engineering", "capex_planning"],
                          ["engineering_specs", "process_docs"], ["operations_roadmap"]),
            RoleBlueprint("process_eng", "Process Engineer", "Manufacturing process optimization",
                          ["process_mapping", "cycle_time_reduction", "waste_elimination"],
                          ["process_improvements"], ["engineering_specs"]),
            RoleBlueprint("maint_lead", "Maintenance Lead", "Equipment maintenance and reliability",
                          ["preventive_maintenance", "spare_parts_mgmt", "downtime_analysis"],
                          ["maintenance_schedules", "equipment_reports"], ["engineering_specs"]),
        ]),
        DeptBlueprint("Supply Chain & Logistics", [
            RoleBlueprint("supply_chain_mgr", "Supply Chain Manager", "End-to-end supply chain",
                          ["demand_planning", "vendor_management", "inventory_optimization"],
                          ["purchase_orders", "raw_material_orders"], ["production_plan"]),
            RoleBlueprint("warehouse_lead", "Warehouse Lead", "Warehousing and distribution",
                          ["inventory_control", "picking_packing", "shipping"],
                          ["shipment_schedules", "inventory_reports"], ["assembled_units"]),
            RoleBlueprint("logistics_coord", "Logistics Coordinator", "Transport and delivery",
                          ["route_planning", "carrier_management", "customs_documentation"],
                          ["delivery_reports"], ["shipment_schedules"]),
        ]),
        DeptBlueprint("Administration & Finance", [
            RoleBlueprint("plant_dir", "Plant Director", "Overall plant performance",
                          ["strategic_planning", "p_and_l_management", "customer_relations"],
                          ["company_strategy", "financial_reports"], ["quality_reports", "operations_roadmap"]),
            RoleBlueprint("hr_admin", "HR Administrator", "Workforce management",
                          ["payroll", "shift_rostering", "training_records"],
                          ["headcount_reports"], ["company_strategy"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("plant_dir", "vp_ops", "governance", True),
        DependencyBlueprint("vp_ops", "prod_mgr_a", "operational", True),
        DependencyBlueprint("vp_ops", "prod_mgr_b", "operational", True),
        DependencyBlueprint("prod_mgr_a", "sr_operator", "operational", True),
        DependencyBlueprint("sr_operator", "operator_1", "operational", False),
        DependencyBlueprint("qa_mgr", "qa_inspector", "governance", True),
        DependencyBlueprint("qa_mgr", "prod_mgr_a", "informational", False),
        DependencyBlueprint("qa_mgr", "prod_mgr_b", "informational", False),
        DependencyBlueprint("safety_officer", "vp_ops", "governance", False),
        DependencyBlueprint("eng_mgr", "process_eng", "operational", True),
        DependencyBlueprint("eng_mgr", "maint_lead", "operational", False),
        DependencyBlueprint("process_eng", "prod_mgr_a", "informational", False),
        DependencyBlueprint("supply_chain_mgr", "warehouse_lead", "operational", True),
        DependencyBlueprint("warehouse_lead", "logistics_coord", "operational", False),
        DependencyBlueprint("supply_chain_mgr", "vp_ops", "informational", False),
        DependencyBlueprint("hr_admin", "plant_dir", "informational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# MANUFACTURING — MATURE
# ═══════════════════════════════════════════════════════════════════════

_MANUFACTURING_MATURE = IndustryTemplate(
    industry="manufacturing",
    stage="mature",
    departments=[
        DeptBlueprint("Production & Assembly", [
            RoleBlueprint("coo", "Chief Operating Officer", "Manufacturing operations strategy",
                          ["operational_strategy", "capex_decisions", "global_expansion"],
                          ["operations_roadmap", "production_plan"], ["company_strategy"]),
            RoleBlueprint("prod_dir_a", "Production Director A", "High-volume line oversight",
                          ["capacity_planning", "lean_management", "team_leadership"],
                          ["line_a_output", "shift_reports"], ["production_plan"]),
            RoleBlueprint("prod_dir_b", "Production Director B", "Specialty line oversight",
                          ["batch_scheduling", "changeover_optimization", "quality_assurance"],
                          ["line_b_output", "quality_logs"], ["production_plan"]),
            RoleBlueprint("sr_operator", "Senior Machine Operator", "Skilled machining",
                          ["cnc_operation", "tooling", "apprentice_training"],
                          ["precision_parts"], ["shift_reports"]),
            RoleBlueprint("assembly_lead", "Assembly Lead", "Final assembly coordination",
                          ["assembly_scheduling", "work_instructions", "quality_checks"],
                          ["assembled_units", "finished_products"], ["precision_parts"]),
        ]),
        DeptBlueprint("Quality Management System", [
            RoleBlueprint("quality_dir", "Quality Director", "Enterprise quality strategy",
                          ["iso_management", "supplier_quality", "continuous_improvement"],
                          ["quality_reports", "compliance_certs"], ["operations_roadmap"]),
            RoleBlueprint("qa_sr", "Senior QA Engineer", "Advanced inspection and testing",
                          ["statistical_process_control", "root_cause_analysis", "audit_management"],
                          ["spc_reports", "inspection_reports"], ["quality_reports"]),
            RoleBlueprint("ehs_mgr", "EHS Manager", "Environmental, health, and safety management",
                          ["safety_programs", "environmental_compliance", "incident_prevention"],
                          ["safety_reports", "ehs_records"], ["shift_reports"]),
        ]),
        DeptBlueprint("Manufacturing Engineering", [
            RoleBlueprint("mfg_eng_dir", "Manufacturing Engineering Director", "Process and automation",
                          ["automation_strategy", "process_engineering", "new_product_introduction"],
                          ["engineering_specs", "process_docs"], ["operations_roadmap"]),
            RoleBlueprint("automation_eng", "Automation Engineer", "Robotics and control systems",
                          ["plc_programming", "robot_integration", "hmi_design"],
                          ["automation_configs"], ["engineering_specs"]),
            RoleBlueprint("maint_mgr", "Maintenance Manager", "Asset reliability and TPM",
                          ["tpm_implementation", "spare_parts_strategy", "cmms_management"],
                          ["maintenance_schedules", "equipment_reports"], ["engineering_specs"]),
            RoleBlueprint("industrial_eng", "Industrial Engineer", "Layout and efficiency",
                          ["time_studies", "layout_optimization", "ergonomics"],
                          ["process_improvements"], ["process_docs"]),
        ]),
        DeptBlueprint("Global Supply Chain", [
            RoleBlueprint("supply_chain_dir", "Supply Chain Director", "Global procurement and logistics",
                          ["global_sourcing", "demand_forecasting", "supplier_development"],
                          ["purchase_orders", "raw_material_orders"], ["production_plan"]),
            RoleBlueprint("procurement_mgr", "Procurement Manager", "Strategic sourcing",
                          ["vendor_negotiations", "contract_management", "cost_reduction"],
                          ["vendor_scorecards"], ["purchase_orders"]),
            RoleBlueprint("logistics_mgr", "Logistics Manager", "Distribution and warehousing",
                          ["3pl_management", "warehouse_optimization", "customs"],
                          ["shipment_schedules", "inventory_reports"], ["finished_products"]),
        ]),
        DeptBlueprint("Corporate Services", [
            RoleBlueprint("ceo", "CEO", "Corporate strategy and governance",
                          ["strategic_planning", "board_management", "investor_relations"],
                          ["company_strategy", "financial_reports"], ["quality_reports", "operations_roadmap"]),
            RoleBlueprint("cfo", "CFO", "Financial strategy and reporting",
                          ["financial_planning", "cost_accounting", "capex_approval"],
                          ["budget_plans"], ["financial_reports"]),
            RoleBlueprint("hr_dir", "HR Director", "Workforce planning and development",
                          ["talent_acquisition", "training_programs", "labor_relations"],
                          ["headcount_reports", "training_plans"], ["company_strategy"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("ceo", "coo", "governance", True),
        DependencyBlueprint("coo", "prod_dir_a", "operational", True),
        DependencyBlueprint("coo", "prod_dir_b", "operational", True),
        DependencyBlueprint("prod_dir_a", "sr_operator", "operational", True),
        DependencyBlueprint("sr_operator", "assembly_lead", "operational", False),
        DependencyBlueprint("quality_dir", "qa_sr", "governance", True),
        DependencyBlueprint("quality_dir", "coo", "informational", False),
        DependencyBlueprint("ehs_mgr", "prod_dir_a", "governance", False),
        DependencyBlueprint("mfg_eng_dir", "automation_eng", "operational", True),
        DependencyBlueprint("mfg_eng_dir", "maint_mgr", "operational", False),
        DependencyBlueprint("mfg_eng_dir", "industrial_eng", "operational", False),
        DependencyBlueprint("maint_mgr", "prod_dir_a", "informational", False),
        DependencyBlueprint("supply_chain_dir", "procurement_mgr", "operational", True),
        DependencyBlueprint("supply_chain_dir", "logistics_mgr", "operational", True),
        DependencyBlueprint("logistics_mgr", "assembly_lead", "operational", False),
        DependencyBlueprint("cfo", "supply_chain_dir", "governance", False),
        DependencyBlueprint("hr_dir", "coo", "informational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# MARKETPLACE — STRUCTURED
# ═══════════════════════════════════════════════════════════════════════

_MARKETPLACE_STRUCTURED = IndustryTemplate(
    industry="marketplace",
    stage="structured",
    departments=[
        DeptBlueprint("Platform Engineering", [
            RoleBlueprint("vp_eng", "VP Engineering", "Platform technical leadership",
                          ["architecture_review", "team_management", "tech_strategy"],
                          ["engineering_roadmap", "technical_decisions"], ["product_roadmap"]),
            RoleBlueprint("backend_lead", "Backend Lead", "Core matching and API services",
                          ["matching_algorithm", "api_architecture", "data_modeling"],
                          ["api_services", "matching_engine"], ["engineering_roadmap"]),
            RoleBlueprint("frontend_lead", "Frontend Lead", "Web and mobile user interfaces",
                          ["responsive_design", "component_architecture", "performance"],
                          ["user_interfaces"], ["api_services", "design_specs"]),
            RoleBlueprint("data_eng", "Data Engineer", "Analytics and ML pipelines",
                          ["etl_pipelines", "data_warehousing", "feature_engineering"],
                          ["analytics_data", "ml_models"], ["api_services"]),
            RoleBlueprint("devops", "DevOps Engineer", "Infrastructure and deployment",
                          ["ci_cd", "cloud_infra", "monitoring"],
                          ["deployment_pipelines", "infra_configs"], ["api_services"]),
        ]),
        DeptBlueprint("Product & Design", [
            RoleBlueprint("head_product", "Head of Product", "Product vision and roadmap",
                          ["product_strategy", "user_research", "prioritization"],
                          ["product_roadmap", "product_requirements"], ["company_strategy"]),
            RoleBlueprint("pm_supply", "PM Supply Side", "Supply-side product features",
                          ["seller_tools", "listing_optimization", "supply_analytics"],
                          ["supply_specs"], ["product_roadmap"]),
            RoleBlueprint("pm_demand", "PM Demand Side", "Buyer experience features",
                          ["search_discovery", "checkout_flow", "personalization"],
                          ["demand_specs"], ["product_roadmap"]),
            RoleBlueprint("ux_designer", "UX Designer", "User experience design",
                          ["user_flows", "wireframing", "usability_testing"],
                          ["design_specs", "prototypes"], ["product_requirements"]),
        ]),
        DeptBlueprint("Supply Operations", [
            RoleBlueprint("supply_dir", "Supply Director", "Supply-side strategy and quality",
                          ["vendor_strategy", "quality_standards", "pricing_policy"],
                          ["supply_strategy", "vendor_scorecards"], ["company_strategy"]),
            RoleBlueprint("supply_ops_lead", "Supply Ops Lead", "Onboarding and performance",
                          ["seller_onboarding", "performance_tracking", "dispute_resolution"],
                          ["supply_metrics", "active_sellers"], ["supply_strategy"]),
            RoleBlueprint("category_mgr", "Category Manager", "Category curation and merchandising",
                          ["category_analysis", "product_curation", "pricing_optimization"],
                          ["category_reports"], ["supply_strategy", "analytics_data"]),
        ]),
        DeptBlueprint("Growth & Marketing", [
            RoleBlueprint("cmo", "Chief Marketing Officer", "Brand and demand generation",
                          ["brand_strategy", "channel_strategy", "budget_management"],
                          ["marketing_plans", "campaign_reports"], ["product_roadmap"]),
            RoleBlueprint("growth_lead", "Growth Lead", "Acquisition and viral loops",
                          ["seo", "paid_ads", "referral_programs", "conversion_optimization"],
                          ["traffic_reports", "marketing_leads"], ["marketing_plans"]),
            RoleBlueprint("content_lead", "Content Lead", "Content strategy and community",
                          ["editorial_calendar", "social_media", "community_engagement"],
                          ["content_assets"], ["marketing_plans"]),
        ]),
        DeptBlueprint("Trust & Safety", [
            RoleBlueprint("trust_dir", "Trust & Safety Director", "Platform integrity strategy",
                          ["fraud_prevention", "policy_development", "regulatory_compliance"],
                          ["trust_reports", "policy_docs"], ["analytics_data"]),
            RoleBlueprint("risk_analyst", "Risk Analyst", "Fraud detection and investigation",
                          ["fraud_investigation", "pattern_analysis", "chargeback_management"],
                          ["risk_reports"], ["trust_reports", "analytics_data"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("vp_eng", "backend_lead", "operational", True),
        DependencyBlueprint("vp_eng", "frontend_lead", "operational", True),
        DependencyBlueprint("vp_eng", "data_eng", "operational", False),
        DependencyBlueprint("vp_eng", "devops", "operational", False),
        DependencyBlueprint("backend_lead", "frontend_lead", "operational", False),
        DependencyBlueprint("head_product", "pm_supply", "governance", True),
        DependencyBlueprint("head_product", "pm_demand", "governance", True),
        DependencyBlueprint("ux_designer", "frontend_lead", "operational", True),
        DependencyBlueprint("pm_demand", "frontend_lead", "operational", False),
        DependencyBlueprint("supply_dir", "supply_ops_lead", "operational", True),
        DependencyBlueprint("supply_dir", "category_mgr", "governance", False),
        DependencyBlueprint("supply_ops_lead", "backend_lead", "operational", False),
        DependencyBlueprint("cmo", "growth_lead", "governance", True),
        DependencyBlueprint("cmo", "content_lead", "governance", False),
        DependencyBlueprint("trust_dir", "risk_analyst", "operational", True),
        DependencyBlueprint("trust_dir", "data_eng", "operational", False),
        DependencyBlueprint("category_mgr", "pm_supply", "informational", False),
        DependencyBlueprint("growth_lead", "data_eng", "informational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# MARKETPLACE — MATURE
# ═══════════════════════════════════════════════════════════════════════

_MARKETPLACE_MATURE = IndustryTemplate(
    industry="marketplace",
    stage="mature",
    departments=[
        DeptBlueprint("Core Platform Engineering", [
            RoleBlueprint("cto", "CTO", "Technical vision and platform strategy",
                          ["platform_architecture", "tech_investment", "build_vs_buy"],
                          ["technical_roadmap", "architecture_decisions"], ["company_strategy"]),
            RoleBlueprint("backend_dir", "Backend Director", "Services and data platform",
                          ["microservice_strategy", "api_governance", "data_architecture"],
                          ["api_services", "data_models"], ["technical_roadmap"]),
            RoleBlueprint("frontend_dir", "Frontend Director", "Client apps and design system",
                          ["mobile_strategy", "web_performance", "design_system"],
                          ["user_interfaces"], ["api_services", "design_specs"]),
            RoleBlueprint("ml_lead", "ML Engineering Lead", "Search, ranking, and recommendations",
                          ["ml_models", "search_relevance", "recommendation_systems"],
                          ["ml_models", "analytics_data"], ["api_services"]),
            RoleBlueprint("infra_lead", "Infrastructure Lead", "Cloud, SRE, and developer experience",
                          ["cloud_architecture", "observability", "developer_tooling"],
                          ["infra_configs", "deployment_pipelines"], ["api_services"]),
        ]),
        DeptBlueprint("Product & Strategy", [
            RoleBlueprint("cpo", "Chief Product Officer", "Product vision and market positioning",
                          ["product_strategy", "competitive_analysis", "okr_setting"],
                          ["product_roadmap", "product_requirements"], ["company_strategy"]),
            RoleBlueprint("pm_marketplace", "PM Marketplace", "Core marketplace mechanics",
                          ["pricing_model", "matching_rules", "transaction_flow"],
                          ["marketplace_specs"], ["product_roadmap"]),
            RoleBlueprint("pm_seller", "PM Seller Experience", "Seller tools and analytics",
                          ["seller_dashboard", "listing_tools", "payout_systems"],
                          ["seller_specs"], ["product_roadmap"]),
            RoleBlueprint("pm_buyer", "PM Buyer Experience", "Buyer journey optimization",
                          ["search_ux", "reviews_ratings", "checkout_optimization"],
                          ["buyer_specs"], ["product_roadmap"]),
            RoleBlueprint("ux_dir", "UX Director", "Design system and research",
                          ["design_strategy", "user_research", "accessibility"],
                          ["design_specs", "prototypes"], ["product_requirements"]),
        ]),
        DeptBlueprint("Supply & Marketplace Operations", [
            RoleBlueprint("vp_supply", "VP Supply", "Supply acquisition and quality",
                          ["supply_strategy", "quality_assurance", "market_expansion"],
                          ["supply_strategy", "vendor_scorecards"], ["company_strategy"]),
            RoleBlueprint("supply_ops_mgr", "Supply Operations Manager", "Day-to-day supply ops",
                          ["onboarding_process", "performance_management", "dispute_resolution"],
                          ["supply_metrics", "active_sellers"], ["supply_strategy"]),
            RoleBlueprint("category_dir", "Category Director", "Category strategy and merchandising",
                          ["category_expansion", "merchandising", "pricing_intelligence"],
                          ["category_reports"], ["supply_strategy", "analytics_data"]),
        ]),
        DeptBlueprint("Growth & Revenue", [
            RoleBlueprint("cmo", "CMO", "Brand, growth, and partnerships",
                          ["brand_strategy", "growth_strategy", "strategic_partnerships"],
                          ["marketing_plans", "campaign_reports"], ["product_roadmap"]),
            RoleBlueprint("growth_dir", "Growth Director", "Paid and organic acquisition",
                          ["channel_optimization", "attribution_modeling", "ltv_analysis"],
                          ["traffic_reports", "marketing_leads"], ["marketing_plans"]),
            RoleBlueprint("partnerships_mgr", "Partnerships Manager", "Strategic alliances",
                          ["partner_acquisition", "integration_programs", "revenue_sharing"],
                          ["partnership_reports"], ["marketing_plans"]),
        ]),
        DeptBlueprint("Trust, Safety & Legal", [
            RoleBlueprint("trust_vp", "VP Trust & Safety", "Platform integrity and compliance",
                          ["fraud_strategy", "content_moderation", "regulatory_affairs"],
                          ["trust_reports", "policy_docs"], ["company_strategy"]),
            RoleBlueprint("fraud_lead", "Fraud Operations Lead", "Fraud detection and prevention",
                          ["ml_fraud_models", "investigation_workflows", "chargeback_ops"],
                          ["fraud_reports"], ["trust_reports", "analytics_data"]),
            RoleBlueprint("legal_counsel", "Legal Counsel", "Marketplace legal compliance",
                          ["terms_of_service", "ip_disputes", "regulatory_filings"],
                          ["legal_opinions"], ["policy_docs"]),
        ]),
        DeptBlueprint("Corporate & Finance", [
            RoleBlueprint("ceo", "CEO", "Company vision and governance",
                          ["corporate_strategy", "fundraising", "board_management"],
                          ["company_strategy"], ["financial_reports"]),
            RoleBlueprint("cfo", "CFO", "Financial strategy and unit economics",
                          ["financial_planning", "unit_economics", "investor_reporting"],
                          ["financial_reports", "budget_plans"], ["campaign_reports"]),
        ]),
    ],
    dependencies=[
        DependencyBlueprint("cto", "backend_dir", "operational", True),
        DependencyBlueprint("cto", "frontend_dir", "operational", True),
        DependencyBlueprint("cto", "ml_lead", "operational", False),
        DependencyBlueprint("cto", "infra_lead", "operational", False),
        DependencyBlueprint("backend_dir", "frontend_dir", "operational", False),
        DependencyBlueprint("cpo", "pm_marketplace", "governance", True),
        DependencyBlueprint("cpo", "pm_seller", "governance", True),
        DependencyBlueprint("cpo", "pm_buyer", "governance", False),
        DependencyBlueprint("ux_dir", "frontend_dir", "operational", True),
        DependencyBlueprint("pm_buyer", "frontend_dir", "operational", False),
        DependencyBlueprint("vp_supply", "supply_ops_mgr", "operational", True),
        DependencyBlueprint("vp_supply", "category_dir", "governance", False),
        DependencyBlueprint("supply_ops_mgr", "backend_dir", "operational", False),
        DependencyBlueprint("category_dir", "pm_seller", "informational", False),
        DependencyBlueprint("cmo", "growth_dir", "governance", True),
        DependencyBlueprint("cmo", "partnerships_mgr", "governance", False),
        DependencyBlueprint("growth_dir", "ml_lead", "informational", False),
        DependencyBlueprint("trust_vp", "fraud_lead", "operational", True),
        DependencyBlueprint("trust_vp", "legal_counsel", "governance", False),
        DependencyBlueprint("fraud_lead", "ml_lead", "operational", False),
        DependencyBlueprint("ceo", "cpo", "governance", False),
        DependencyBlueprint("ceo", "cto", "governance", False),
        DependencyBlueprint("cfo", "cmo", "informational", False),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATE REGISTRY
# ═══════════════════════════════════════════════════════════════════════

# Keyed by (industry, stage).
# If exact stage not found, falls back to closest lower stage.
_REGISTRY: Dict[tuple, IndustryTemplate] = {
    ("tech_saas", "seed"): _TECH_SAAS_SEED,
    ("tech_saas", "growth"): _TECH_SAAS_GROWTH,
    ("tech_saas", "structured"): _TECH_SAAS_STRUCTURED,
    ("tech_saas", "mature"): _TECH_SAAS_MATURE,
    ("manufacturing", "seed"): _MANUFACTURING_SEED,
    ("manufacturing", "growth"): _MANUFACTURING_GROWTH,
    ("manufacturing", "structured"): _MANUFACTURING_STRUCTURED,
    ("manufacturing", "mature"): _MANUFACTURING_MATURE,
    ("marketplace", "seed"): _MARKETPLACE_SEED,
    ("marketplace", "growth"): _MARKETPLACE_GROWTH,
    ("marketplace", "structured"): _MARKETPLACE_STRUCTURED,
    ("marketplace", "mature"): _MARKETPLACE_MATURE,
}

_STAGE_ORDER = ["seed", "growth", "structured", "mature"]


def get_template(industry: str, stage: str) -> IndustryTemplate:
    """Look up the best-fit template for industry × stage."""
    key = (industry, stage)
    if key in _REGISTRY:
        return _REGISTRY[key]

    # Fallback: find closest lower stage
    stage_idx = _STAGE_ORDER.index(stage) if stage in _STAGE_ORDER else 0
    for i in range(stage_idx, -1, -1):
        fallback = (industry, _STAGE_ORDER[i])
        if fallback in _REGISTRY:
            return _REGISTRY[fallback]

    # Ultimate fallback
    return _TECH_SAAS_SEED
