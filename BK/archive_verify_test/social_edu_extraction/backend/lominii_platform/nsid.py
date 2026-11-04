"""Namespace Identifiers (Platform Layer)"""

class NSID:
    SEARCH = 0
    SOCIAL = 1
    EDU = 2
    GAMES = 3
    SHOP = 4
    CRAWLER = 5
    ADMIN = 6
    SYSTEM = 7

    @classmethod
    def name(cls, nsid: int) -> str:
        names = {
            0: "Search", 1: "Social", 2: "EDU", 3: "Games",
            4: "Shop", 5: "Crawler", 6: "Admin", 7: "System"
        }
        return names.get(nsid, "Unknown")