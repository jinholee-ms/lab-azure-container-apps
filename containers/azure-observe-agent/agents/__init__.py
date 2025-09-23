from .azure import AzureInventoryAgent
from .travel import JourneyDiscoveryAgent


agents_collection = {
    "Azure Inventory Agent": AzureInventoryAgent,
    "Journey Discovery Agent": JourneyDiscoveryAgent,
}


__all__ = ["AzureInventoryAgent", "JourneyDiscoveryAgent"]