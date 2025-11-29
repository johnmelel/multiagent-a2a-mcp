import sqlite3
import os

class DatabaseSetup:
    """SQLite database setup for customer support system."""

    def __init__(self, db_path: str = "data/customers.db"):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        self.cursor = self.conn.cursor()
        print(f"Connected to database: {self.db_path}")

    def create_tables(self):
        """Create customers and tickets tables."""

        # Create customers table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create tickets table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved')),
                priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better query performance
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)
        """)

        self.conn.commit()
        print("Tables created successfully!")

    def create_triggers(self):
        """Create triggers for automatic timestamp updates."""

        # Trigger to update updated_at on customers table
        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_customer_timestamp
            AFTER UPDATE ON customers
            FOR EACH ROW
            BEGIN
                UPDATE customers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        self.conn.commit()
        print("Triggers created successfully!")

    def insert_sample_data(self):
        """Insert sample data for testing."""
        
        # Check if data already exists to avoid duplicates if run multiple times
        self.cursor.execute("SELECT COUNT(*) FROM customers")
        if self.cursor.fetchone()[0] > 0:
            print("Data already exists, skipping insertion.")
            return

        # Sample customers (15 customers with diverse data)
        # Explicitly setting IDs for required scenarios
        customers = [
            (5, "Test User 5", "user5@example.com", "+1-555-0005", "active"),
            (12345, "Premium User", "premium@example.com", "+1-555-12345", "active"),
            (1, "John Doe", "john.doe@example.com", "+1-555-0101", "active"),
            (2, "Jane Smith", "jane.smith@example.com", "+1-555-0102", "active"),
            (3, "Bob Johnson", "bob.johnson@example.com", "+1-555-0103", "disabled"),
            (4, "Alice Williams", "alice.w@techcorp.com", "+1-555-0104", "active"),
            (6, "Charlie Brown", "charlie.brown@email.com", "+1-555-0105", "active"),
            (7, "Diana Prince", "diana.prince@company.org", "+1-555-0106", "active"),
            (8, "Edward Norton", "e.norton@business.net", "+1-555-0107", "active"),
            (9, "Fiona Green", "fiona.green@startup.io", "+1-555-0108", "disabled"),
            (10, "George Miller", "george.m@enterprise.com", "+1-555-0109", "active"),
            (11, "Hannah Lee", "hannah.lee@global.com", "+1-555-0110", "active"),
            (12, "Isaac Newton", "isaac.n@science.edu", "+1-555-0111", "active"),
            (13, "Julia Roberts", "julia.r@movies.com", "+1-555-0112", "active"),
            (14, "Kevin Chen", "kevin.chen@tech.io", "+1-555-0113", "disabled"),
            (15, "Laura Martinez", "laura.m@solutions.com", "+1-555-0114", "active"),
            (16, "Michael Scott", "michael.scott@paper.com", "+1-555-0115", "active"),
        ]

        self.cursor.executemany("""
            INSERT OR IGNORE INTO customers (id, name, email, phone, status)
            VALUES (?, ?, ?, ?, ?)
        """, customers)

        # Sample tickets (25 tickets with various statuses and priorities)
        tickets = [
            # High priority tickets
            (1, "Cannot login to account", "open", "high"),
            (4, "Database connection timeout errors", "in_progress", "high"),
            (7, "Payment processing failing for all transactions", "open", "high"),
            (10, "Critical security vulnerability found", "in_progress", "high"),
            (14, "Website completely down", "resolved", "high"),
            (12345, "Need help upgrading my account", "open", "medium"), # For scenario 2

            # Medium priority tickets
            (1, "Password reset not working", "in_progress", "medium"),
            (2, "Profile image upload fails", "resolved", "medium"),
            (5, "Email notifications not being received", "open", "medium"),
            (6, "Dashboard loading very slowly", "in_progress", "medium"),
            (9, "Export to CSV feature broken", "open", "medium"),
            (11, "Mobile app crashes on startup", "resolved", "medium"),
            (12, "Search functionality returning wrong results", "in_progress", "medium"),
            (15, "API rate limiting too restrictive", "open", "medium"),

            # Low priority tickets
            (2, "Billing question about invoice", "resolved", "low"),
            (2, "Feature request: dark mode", "open", "low"),
            (3, "Documentation outdated for API v2", "open", "low"),
            (5, "Typo in welcome email", "resolved", "low"),
            (6, "Request for additional language support", "open", "low"),
            (9, "Font size too small on settings page", "resolved", "low"),
            (11, "Feature request: export to PDF", "open", "low"),
            (12, "Color scheme suggestion for better contrast", "open", "low"),
            (14, "Request access to beta features", "in_progress", "low"),
            (15, "Question about pricing plans", "resolved", "low"),
            (4, "Feature request: integration with Slack", "open", "low"),
            (10, "Suggestion: add keyboard shortcuts", "open", "low"),
        ]

        self.cursor.executemany("""
            INSERT INTO tickets (customer_id, issue, status, priority)
            VALUES (?, ?, ?, ?)
        """, tickets)

        self.conn.commit()
        print("Sample data inserted successfully!")
        print(f"  - {len(customers)} customers added")
        print(f"  - {len(tickets)} tickets added")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")


def main():
    """Main function to setup the database."""

    # Initialize database
    db = DatabaseSetup("data/customers.db")

    try:
        # Connect to database
        db.connect()

        # Create tables
        db.create_tables()

        # Create triggers
        db.create_triggers()

        # Insert sample data
        db.insert_sample_data()

        print("\n✓ Database setup complete!")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
