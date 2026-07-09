import shutil
from datetime import datetime

from config import DATABASE_NAME



backup_name = (
    f"backup_tutoring_portal_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)



shutil.copy2(
    DATABASE_NAME,
    backup_name
)



print(
    f"Backup created: {backup_name}"
)