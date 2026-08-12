import unittest
from unittest.mock import patch
import uuid
from datetime import date
from decimal import Decimal
from app.database.session import SessionLocal
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.statement import Statement, StatementStatus
from app.repositories.statement_repository import StatementRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.services.statement_service import StatementService
from app.services.transaction_service import TransactionService

class StatementImportTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Create a unique test user for each test to completely avoid database state contamination
        self.unique_email = f"test_{uuid.uuid4().hex}@example.com"
        self.user = User(
            full_name="Import Test User",
            email=self.unique_email,
            hashed_password="mocked_password"
        )
        self.db.add(self.user)
        self.db.commit() # Commit user so they are in the DB and have an ID
        
        # Create a test account for this user
        self.account = Account(
            user_id=self.user.id,
            name="Test Checking",
            account_type="Checking",
            balance=Decimal("10000.00"),
            currency="INR"
        )
        self.db.add(self.account)
        self.db.commit()
        
        # Instantiate services
        self.statement_repo = StatementRepository(self.db)
        self.transaction_repo = TransactionRepository(self.db)
        self.account_repo = AccountRepository(self.db)
        self.category_repo = CategoryRepository(self.db)
        self.transaction_service = TransactionService(
            self.transaction_repo,
            self.account_repo,
            self.category_repo
        )
        self.statement_service = StatementService(
            self.statement_repo,
            self.transaction_repo,
            self.account_repo,
            self.category_repo,
            self.transaction_service
        )

    def tearDown(self):
        # Explicitly delete all records in the dependency order to avoid RESTRICT foreign key constraint failures
        self.db.query(Transaction).filter_by(user_id=self.user.id).delete()
        self.db.query(Statement).filter_by(user_id=self.user.id).delete()
        self.db.query(Account).filter_by(user_id=self.user.id).delete()
        self.db.query(Category).filter_by(user_id=self.user.id).delete()
        self.db.query(User).filter_by(id=self.user.id).delete()
        self.db.commit()
        self.db.close()

    def test_category_preservation(self):
        csv_data = (
            "Date,Title,Type,Amount,Account,Category,Merchant,Tags\n"
            "2026-07-01,Lunch,Expense,15.50,Test Checking,Food,Local Diner,fun\n"
        ).encode("utf-8")
        
        preview = self.statement_service.preview_upload(
            user_id=self.user.id,
            account_id=self.account.id,
            filename="statement.csv",
            content_type="text/csv",
            data=csv_data
        )
        
        # Verify preview category is resolved to "Food" (which is seeded)
        self.assertEqual(preview.preview_transactions[0].category, "Food")
        
        # Import the statement
        res = self.statement_service.import_statement(self.user.id, preview.statement_id)
        self.assertEqual(res.imported_transactions, 1)
        
        # Retrieve the transaction
        tx = self.db.query(Transaction).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(tx)
        
        # Retrieve category
        category = self.db.get(Category, tx.category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category.name, "Food")

    def test_title_preservation(self):
        csv_data = (
            "Date,Title,Type,Amount,Account,Category,Merchant,Tags\n"
            "2026-07-01,Freelance,Income,1057.58,Test Checking,Salary,Employer,fun\n"
        ).encode("utf-8")
        
        preview = self.statement_service.preview_upload(
            user_id=self.user.id,
            account_id=self.account.id,
            filename="statement.csv",
            content_type="text/csv",
            data=csv_data
        )
        
        # Verify preview title is parsed as "Freelance"
        self.assertEqual(preview.preview_transactions[0].title, "Freelance")
        
        # Import the statement
        res = self.statement_service.import_statement(self.user.id, preview.statement_id)
        self.assertEqual(res.imported_transactions, 1)
        
        # Retrieve transaction
        tx = self.db.query(Transaction).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.title, "Freelance")
        self.assertEqual(tx.merchant, "Employer")

    def test_income_category_preservation(self):
        csv_data = (
            "Date,Title,Type,Amount,Account,Category,Merchant,Tags\n"
            "2026-07-01,Freelance,Income,1057.58,Test Checking,Income,Employer,fun\n"
        ).encode("utf-8")
        
        preview = self.statement_service.preview_upload(
            user_id=self.user.id,
            account_id=self.account.id,
            filename="statement.csv",
            content_type="text/csv",
            data=csv_data
        )
        
        # Verify preview category is "Income"
        self.assertEqual(preview.preview_transactions[0].category, "Income")
        self.assertEqual(preview.preview_transactions[0].transaction_type, TransactionType.INCOME)
        
        # Import the statement
        res = self.statement_service.import_statement(self.user.id, preview.statement_id)
        self.assertEqual(res.imported_transactions, 1)
        
        # Retrieve transaction
        tx = self.db.query(Transaction).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.transaction_type, TransactionType.INCOME)
        
        # Retrieve category
        category = self.db.get(Category, tx.category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category.name, "Income")

    def test_expense_category_preservation(self):
        csv_data = (
            "Date,Title,Type,Amount,Account,Category,Merchant,Tags\n"
            "2026-07-01,Restaurant,Expense,150.00,Test Checking,Food,Local Diner,fun\n"
        ).encode("utf-8")
        
        preview = self.statement_service.preview_upload(
            user_id=self.user.id,
            account_id=self.account.id,
            filename="statement.csv",
            content_type="text/csv",
            data=csv_data
        )
        
        # Verify preview
        self.assertEqual(preview.preview_transactions[0].category, "Food")
        self.assertEqual(preview.preview_transactions[0].transaction_type, TransactionType.EXPENSE)
        
        # Import
        res = self.statement_service.import_statement(self.user.id, preview.statement_id)
        self.assertEqual(res.imported_transactions, 1)
        
        # Retrieve transaction
        tx = self.db.query(Transaction).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.transaction_type, TransactionType.EXPENSE)
        
        # Retrieve category
        category = self.db.get(Category, tx.category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category.name, "Food")

    @patch("app.ai.llm_gateway.LLMGateway.generate")
    def test_unknown_category_fallback(self, mock_generate):
        # Simulate LLM failing to classify the transaction
        mock_generate.side_effect = Exception("Simulated LLM failure")
        
        csv_data = (
            "Date,Title,Type,Amount,Account,Category,Merchant,Tags\n"
            "2026-07-01,Some Random Tx,Expense,50.00,Test Checking,,Random Merchant,fun\n"
        ).encode("utf-8")
        
        preview = self.statement_service.preview_upload(
            user_id=self.user.id,
            account_id=self.account.id,
            filename="statement.csv",
            content_type="text/csv",
            data=csv_data
        )
        
        # Falls back to "Uncategorized" since category not provided and LLM failed
        self.assertEqual(preview.preview_transactions[0].category, "Uncategorized")
        
        # Import
        res = self.statement_service.import_statement(self.user.id, preview.statement_id)
        self.assertEqual(res.imported_transactions, 1)
        
        # Retrieve transaction
        tx = self.db.query(Transaction).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(tx)
        
        # Retrieve category
        category = self.db.get(Category, tx.category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category.name, "Uncategorized")
