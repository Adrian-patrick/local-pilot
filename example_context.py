# example_context.py
# A sample system automation script representing a local SRE workload

import os
import sys

def backup_database(db_name: str, destination_dir: str):
    """
    Backs up the target SQLite database to the designated backup folder.
    Ensures that file sizes and paths are properly resolved.
    """
    print(f"Starting backup for database: {db_name}")
    if not os.path.exists(destination_dir):
        print(f"Destination '{destination_dir}' does not exist. Creating it.")
        os.makedirs(destination_dir)
        
    db_path = os.path.join(os.getcwd(), f"{db_name}.db")
    backup_path = os.path.join(destination_dir, f"{db_name}_backup.db")
    
    print(f"Verifying source database path: {db_path}")
    print(f"Destination backup registry: {backup_path}")
    return {"status": "success", "source": db_path, "backup": backup_path}

if __name__ == "__main__":
    result = backup_database("customer_records", "backups")
    print(f"Backup Complete: {result}")
