"""Public platform statistics for the homepage."""
from pydantic import BaseModel


class PlatformStats(BaseModel):
    shops_analyzed: int
    scam_sites_blocked: int
    users_protected: int
