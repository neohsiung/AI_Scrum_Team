from agents.scrum_master import ScrumMasterAgent
from agents.product_owner import ProductOwnerAgent
from agents.tech_lead import TechLeadAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.app import AppAgent
from agents.qa import QAAgent
from agents.devops import DevOpsAgent
from agents.uiux import UIUXAgent
from agents.human_proxy import HumanProxyAgent

ALL_AGENTS = {
    "scrum_master": ScrumMasterAgent,
    "product_owner": ProductOwnerAgent,
    "tech_lead": TechLeadAgent,
    "backend": BackendAgent,
    "frontend": FrontendAgent,
    "app": AppAgent,
    "qa": QAAgent,
    "devops": DevOpsAgent,
    "uiux": UIUXAgent,
    "human_proxy": HumanProxyAgent,
}

__all__ = [
    "ScrumMasterAgent",
    "ProductOwnerAgent",
    "TechLeadAgent",
    "BackendAgent",
    "FrontendAgent",
    "AppAgent",
    "QAAgent",
    "DevOpsAgent",
    "UIUXAgent",
    "HumanProxyAgent",
    "ALL_AGENTS",
]
