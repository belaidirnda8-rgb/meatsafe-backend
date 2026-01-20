#!/usr/bin/env python3
"""
MeatSafe API Backend Testing Suite
Tests all backend endpoints as requested in the review.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sys
import base64

# Configuration
BASE_URL = "https://meat-inspection-1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class MeatSafeAPITester:
    def __init__(self):
        self.admin_token = None
        self.inspector_token = None
        self.admin_user_id = None
        self.inspector_user_id = None
        self.slaughterhouse_id = None
        self.seizure_ids = []
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", status_code: int = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if status_code:
            print(f"    Status Code: {status_code}")
        print()

    def setup_test_data(self):
        """Setup initial test data in MongoDB"""
        print("=== SETTING UP TEST DATA ===")
        
        # We need to manually insert an admin user into MongoDB
        # Since we can't create users without being admin, we'll insert directly
        try:
            from pymongo import MongoClient
            from passlib.context import CryptContext
            from bson import ObjectId
            
            # Connect to MongoDB
            client = MongoClient("mongodb://localhost:27017")
            db = client["meatsafe_db"]
            
            # Setup password hashing
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Create admin user
            admin_password_hash = pwd_context.hash("admin123")
            admin_doc = {
                "_id": ObjectId(),
                "email": "admin@meatsafe.com",
                "password_hash": admin_password_hash,
                "role": "admin",
                "slaughterhouse_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Check if admin already exists
            existing_admin = db.users.find_one({"email": "admin@meatsafe.com"})
            if not existing_admin:
                result = db.users.insert_one(admin_doc)
                self.admin_user_id = str(result.inserted_id)
                print(f"✅ Created admin user with ID: {self.admin_user_id}")
            else:
                self.admin_user_id = str(existing_admin["_id"])
                print(f"✅ Admin user already exists with ID: {self.admin_user_id}")
                
            client.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup test data: {str(e)}")
            return False

    def test_admin_login(self):
        """Test admin login with OAuth2PasswordRequestForm"""
        print("=== TESTING AUTHENTICATION ===")
        
        # Test admin login
        login_data = {
            "username": "admin@meatsafe.com",  # OAuth2 uses 'username' field
            "password": "admin123"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                data=login_data,  # x-www-form-urlencoded
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.log_result("Admin Login", True, f"Token received: {self.admin_token[:20]}...", response.status_code)
                return True
            else:
                self.log_result("Admin Login", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False

    def test_users_me(self):
        """Test /api/users/me endpoint with JWT token"""
        if not self.admin_token:
            self.log_result("GET /users/me", False, "No admin token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{BASE_URL}/users/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /users/me", True, f"User info: {data['email']}, role: {data['role']}", response.status_code)
                return True
            else:
                self.log_result("GET /users/me", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("GET /users/me", False, f"Exception: {str(e)}")
            return False

    def test_create_slaughterhouse(self):
        """Test creating a slaughterhouse (admin only)"""
        print("=== TESTING SLAUGHTERHOUSE MANAGEMENT ===")
        
        if not self.admin_token:
            self.log_result("POST /slaughterhouses", False, "No admin token available")
            return False
            
        slaughterhouse_data = {
            "name": "Abattoir Test Lyon",
            "code": "ATL001",
            "location": "Lyon, France"
        }
        
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{BASE_URL}/slaughterhouses",
                json=slaughterhouse_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.slaughterhouse_id = data["id"]
                self.log_result("POST /slaughterhouses", True, f"Created slaughterhouse ID: {self.slaughterhouse_id}", response.status_code)
                return True
            else:
                self.log_result("POST /slaughterhouses", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("POST /slaughterhouses", False, f"Exception: {str(e)}")
            return False

    def test_list_slaughterhouses(self):
        """Test listing slaughterhouses"""
        if not self.admin_token:
            self.log_result("GET /slaughterhouses", False, "No admin token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{BASE_URL}/slaughterhouses", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /slaughterhouses", True, f"Found {len(data)} slaughterhouses", response.status_code)
                return True
            else:
                self.log_result("GET /slaughterhouses", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("GET /slaughterhouses", False, f"Exception: {str(e)}")
            return False

    def test_get_slaughterhouse_by_id(self):
        """Test getting slaughterhouse by ID"""
        if not self.admin_token or not self.slaughterhouse_id:
            self.log_result("GET /slaughterhouses/{id}", False, "No admin token or slaughterhouse ID available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{BASE_URL}/slaughterhouses/{self.slaughterhouse_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /slaughterhouses/{id}", True, f"Retrieved slaughterhouse: {data['name']}", response.status_code)
                return True
            else:
                self.log_result("GET /slaughterhouses/{id}", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("GET /slaughterhouses/{id}", False, f"Exception: {str(e)}")
            return False

    def test_update_slaughterhouse(self):
        """Test updating slaughterhouse"""
        if not self.admin_token or not self.slaughterhouse_id:
            self.log_result("PUT /slaughterhouses/{id}", False, "No admin token or slaughterhouse ID available")
            return False
            
        update_data = {
            "name": "Abattoir Test Lyon - Modifié",
            "location": "Lyon Centre, France"
        }
        
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.put(
                f"{BASE_URL}/slaughterhouses/{self.slaughterhouse_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("PUT /slaughterhouses/{id}", True, f"Updated slaughterhouse: {data['name']}", response.status_code)
                return True
            else:
                self.log_result("PUT /slaughterhouses/{id}", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("PUT /slaughterhouses/{id}", False, f"Exception: {str(e)}")
            return False

    def test_create_inspector_user(self):
        """Test creating an inspector user (admin only)"""
        print("=== TESTING USER MANAGEMENT ===")
        
        if not self.admin_token or not self.slaughterhouse_id:
            self.log_result("POST /users (inspector)", False, "No admin token or slaughterhouse ID available")
            return False
            
        inspector_data = {
            "email": "inspector@meatsafe.com",
            "password": "inspector123",
            "role": "inspector",
            "slaughterhouse_id": self.slaughterhouse_id
        }
        
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{BASE_URL}/users",
                json=inspector_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.inspector_user_id = data["id"]
                self.log_result("POST /users (inspector)", True, f"Created inspector ID: {self.inspector_user_id}", response.status_code)
                return True
            else:
                self.log_result("POST /users (inspector)", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("POST /users (inspector)", False, f"Exception: {str(e)}")
            return False

    def test_list_users(self):
        """Test listing users with filters"""
        if not self.admin_token:
            self.log_result("GET /users", False, "No admin token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            # Test without filters
            response = requests.get(f"{BASE_URL}/users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /users (no filters)", True, f"Found {len(data)} users", response.status_code)
            else:
                self.log_result("GET /users (no filters)", False, f"Response: {response.text}", response.status_code)
                return False
            
            # Test with role filter
            response = requests.get(f"{BASE_URL}/users?role=inspector", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /users (role=inspector)", True, f"Found {len(data)} inspectors", response.status_code)
            else:
                self.log_result("GET /users (role=inspector)", False, f"Response: {response.text}", response.status_code)
                return False
                
            # Test with slaughterhouse_id filter
            if self.slaughterhouse_id:
                response = requests.get(f"{BASE_URL}/users?slaughterhouse_id={self.slaughterhouse_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result("GET /users (slaughterhouse_id filter)", True, f"Found {len(data)} users for slaughterhouse", response.status_code)
                else:
                    self.log_result("GET /users (slaughterhouse_id filter)", False, f"Response: {response.text}", response.status_code)
                    return False
                    
            return True
                
        except Exception as e:
            self.log_result("GET /users", False, f"Exception: {str(e)}")
            return False

    def test_inspector_login(self):
        """Test inspector login"""
        login_data = {
            "username": "inspector@meatsafe.com",
            "password": "inspector123"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.inspector_token = data["access_token"]
                self.log_result("Inspector Login", True, f"Token received: {self.inspector_token[:20]}...", response.status_code)
                return True
            else:
                self.log_result("Inspector Login", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("Inspector Login", False, f"Exception: {str(e)}")
            return False

    def test_create_seizure_inspector(self):
        """Test creating seizure records as inspector"""
        print("=== TESTING SEIZURE RECORDS (INSPECTOR) ===")
        
        if not self.inspector_token:
            self.log_result("POST /seizures (inspector)", False, "No inspector token available")
            return False
            
        # Create multiple seizures for testing
        seizures_data = [
            {
                "species": "bovine",
                "seized_part": "liver",
                "seizure_type": "partial",
                "reason": "Lésions parasitaires",
                "quantity": 2,
                "unit": "kg",
                "notes": "Présence de kystes hydatiques",
                "photos": [base64.b64encode(b"fake_image_data_1").decode()]
            },
            {
                "species": "porcine",
                "seized_part": "carcass",
                "seizure_type": "total",
                "reason": "Contamination bactérienne",
                "quantity": 1,
                "unit": "pieces",
                "notes": "Carcasse entière saisie"
            },
            {
                "species": "ovine",
                "seized_part": "lung",
                "seizure_type": "partial",
                "reason": "Pneumonie",
                "quantity": 500,
                "unit": "g"
            }
        ]
        
        try:
            headers = {
                "Authorization": f"Bearer {self.inspector_token}",
                "Content-Type": "application/json"
            }
            
            for i, seizure_data in enumerate(seizures_data):
                response = requests.post(
                    f"{BASE_URL}/seizures",
                    json=seizure_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.seizure_ids.append(data["id"])
                    self.log_result(f"POST /seizures (inspector) #{i+1}", True, f"Created seizure ID: {data['id']}", response.status_code)
                else:
                    self.log_result(f"POST /seizures (inspector) #{i+1}", False, f"Response: {response.text}", response.status_code)
                    return False
                    
            return True
                
        except Exception as e:
            self.log_result("POST /seizures (inspector)", False, f"Exception: {str(e)}")
            return False

    def test_list_seizures_inspector(self):
        """Test listing seizures as inspector (should only see own slaughterhouse)"""
        if not self.inspector_token:
            self.log_result("GET /seizures (inspector)", False, "No inspector token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.inspector_token}",
                "Content-Type": "application/json"
            }
            
            # Test without filters
            response = requests.get(f"{BASE_URL}/seizures", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (inspector, no filters)", True, f"Found {data['total']} seizures", response.status_code)
            else:
                self.log_result("GET /seizures (inspector, no filters)", False, f"Response: {response.text}", response.status_code)
                return False
            
            # Test with species filter
            response = requests.get(f"{BASE_URL}/seizures?species=bovine", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (inspector, species=bovine)", True, f"Found {data['total']} bovine seizures", response.status_code)
            else:
                self.log_result("GET /seizures (inspector, species=bovine)", False, f"Response: {response.text}", response.status_code)
                return False
                
            # Test with reason filter
            response = requests.get(f"{BASE_URL}/seizures?reason=Pneumonie", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (inspector, reason=Pneumonie)", True, f"Found {data['total']} pneumonia seizures", response.status_code)
            else:
                self.log_result("GET /seizures (inspector, reason=Pneumonie)", False, f"Response: {response.text}", response.status_code)
                return False
                
            # Test with pagination
            response = requests.get(f"{BASE_URL}/seizures?page=1&page_size=2", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (inspector, pagination)", True, f"Page 1: {len(data['items'])} items, total: {data['total']}", response.status_code)
            else:
                self.log_result("GET /seizures (inspector, pagination)", False, f"Response: {response.text}", response.status_code)
                return False
                
            # Test with date range
            start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
            end_date = datetime.utcnow().isoformat()
            response = requests.get(f"{BASE_URL}/seizures?start_date={start_date}&end_date={end_date}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (inspector, date range)", True, f"Found {data['total']} seizures in date range", response.status_code)
            else:
                self.log_result("GET /seizures (inspector, date range)", False, f"Response: {response.text}", response.status_code)
                return False
                
            return True
                
        except Exception as e:
            self.log_result("GET /seizures (inspector)", False, f"Exception: {str(e)}")
            return False

    def test_get_seizure_by_id_inspector(self):
        """Test getting seizure by ID as inspector"""
        if not self.inspector_token or not self.seizure_ids:
            self.log_result("GET /seizures/{id} (inspector)", False, "No inspector token or seizure IDs available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.inspector_token}",
                "Content-Type": "application/json"
            }
            
            seizure_id = self.seizure_ids[0]
            response = requests.get(f"{BASE_URL}/seizures/{seizure_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures/{id} (inspector)", True, f"Retrieved seizure: {data['species']} - {data['reason']}", response.status_code)
                return True
            else:
                self.log_result("GET /seizures/{id} (inspector)", False, f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("GET /seizures/{id} (inspector)", False, f"Exception: {str(e)}")
            return False

    def test_seizures_admin(self):
        """Test seizure operations as admin"""
        print("=== TESTING SEIZURE RECORDS (ADMIN) ===")
        
        if not self.admin_token:
            self.log_result("Seizures (admin)", False, "No admin token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            # Test GET all seizures (admin should see all)
            response = requests.get(f"{BASE_URL}/seizures", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /seizures (admin)", True, f"Admin can see {data['total']} total seizures", response.status_code)
            else:
                self.log_result("GET /seizures (admin)", False, f"Response: {response.text}", response.status_code)
                return False
            
            # Test GET seizure by ID (admin should access any)
            if self.seizure_ids:
                seizure_id = self.seizure_ids[0]
                response = requests.get(f"{BASE_URL}/seizures/{seizure_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result("GET /seizures/{id} (admin)", True, f"Admin accessed seizure: {data['species']}", response.status_code)
                else:
                    self.log_result("GET /seizures/{id} (admin)", False, f"Response: {response.text}", response.status_code)
                    return False
            
            # Test DELETE seizure (admin only)
            if self.seizure_ids:
                seizure_id = self.seizure_ids[-1]  # Delete the last one
                response = requests.delete(f"{BASE_URL}/seizures/{seizure_id}", headers=headers)
                
                if response.status_code == 204:
                    self.log_result("DELETE /seizures/{id} (admin)", True, f"Deleted seizure ID: {seizure_id}", response.status_code)
                    self.seizure_ids.remove(seizure_id)
                else:
                    self.log_result("DELETE /seizures/{id} (admin)", False, f"Response: {response.text}", response.status_code)
                    return False
                    
            # Test DELETE non-existent seizure (should return 404)
            fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
            response = requests.delete(f"{BASE_URL}/seizures/{fake_id}", headers=headers)
            
            if response.status_code == 404:
                self.log_result("DELETE /seizures/{id} (non-existent)", True, "Correctly returned 404 for non-existent seizure", response.status_code)
            else:
                self.log_result("DELETE /seizures/{id} (non-existent)", False, f"Expected 404, got {response.status_code}", response.status_code)
                
            return True
                
        except Exception as e:
            self.log_result("Seizures (admin)", False, f"Exception: {str(e)}")
            return False

    def test_analytics_admin(self):
        """Test analytics endpoints (admin only)"""
        print("=== TESTING ANALYTICS (ADMIN) ===")
        
        if not self.admin_token:
            self.log_result("Analytics (admin)", False, "No admin token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            # Test analytics without filters
            response = requests.get(f"{BASE_URL}/analytics/summary", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /analytics/summary (no filters)", True, 
                              f"Total cases: {data['total_cases']}, Species: {len(data['by_species'])}, Reasons: {len(data['by_reason'])}", 
                              response.status_code)
            else:
                self.log_result("GET /analytics/summary (no filters)", False, f"Response: {response.text}", response.status_code)
                return False
            
            # Test analytics with date filters
            start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
            end_date = datetime.utcnow().isoformat()
            response = requests.get(f"{BASE_URL}/analytics/summary?start_date={start_date}&end_date={end_date}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /analytics/summary (date filters)", True, 
                              f"Total cases in range: {data['total_cases']}", 
                              response.status_code)
            else:
                self.log_result("GET /analytics/summary (date filters)", False, f"Response: {response.text}", response.status_code)
                return False
                
            # Test analytics with slaughterhouse filter
            if self.slaughterhouse_id:
                response = requests.get(f"{BASE_URL}/analytics/summary?slaughterhouse_id={self.slaughterhouse_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result("GET /analytics/summary (slaughterhouse filter)", True, 
                                  f"Cases for slaughterhouse: {data['total_cases']}", 
                                  response.status_code)
                else:
                    self.log_result("GET /analytics/summary (slaughterhouse filter)", False, f"Response: {response.text}", response.status_code)
                    return False
                    
            return True
                
        except Exception as e:
            self.log_result("Analytics (admin)", False, f"Exception: {str(e)}")
            return False

    def test_delete_slaughterhouse_with_seizures(self):
        """Test that slaughterhouse deletion fails when seizures exist"""
        if not self.admin_token or not self.slaughterhouse_id:
            self.log_result("DELETE /slaughterhouses/{id} (with seizures)", False, "No admin token or slaughterhouse ID available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.delete(f"{BASE_URL}/slaughterhouses/{self.slaughterhouse_id}", headers=headers)
            
            if response.status_code == 400:
                self.log_result("DELETE /slaughterhouses/{id} (with seizures)", True, "Correctly prevented deletion of slaughterhouse with seizures", response.status_code)
                return True
            else:
                self.log_result("DELETE /slaughterhouses/{id} (with seizures)", False, f"Expected 400, got {response.status_code}: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("DELETE /slaughterhouses/{id} (with seizures)", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 STARTING MEATSAFE API TESTING SUITE")
        print("=" * 50)
        
        # Setup
        if not self.setup_test_data():
            print("❌ Failed to setup test data. Aborting tests.")
            return False
            
        # Authentication tests
        if not self.test_admin_login():
            print("❌ Admin login failed. Aborting tests.")
            return False
            
        if not self.test_users_me():
            print("❌ /users/me test failed.")
            
        # Slaughterhouse management tests
        if not self.test_create_slaughterhouse():
            print("❌ Slaughterhouse creation failed. Some tests may fail.")
            
        self.test_list_slaughterhouses()
        self.test_get_slaughterhouse_by_id()
        self.test_update_slaughterhouse()
        
        # User management tests
        if not self.test_create_inspector_user():
            print("❌ Inspector creation failed. Inspector tests may fail.")
            
        self.test_list_users()
        
        # Inspector authentication and seizure tests
        if not self.test_inspector_login():
            print("❌ Inspector login failed. Inspector seizure tests may fail.")
        else:
            self.test_create_seizure_inspector()
            self.test_list_seizures_inspector()
            self.test_get_seizure_by_id_inspector()
            
        # Admin seizure and analytics tests
        self.test_seizures_admin()
        self.test_analytics_admin()
        
        # Edge case tests
        self.test_delete_slaughterhouse_with_seizures()
        
        # Print summary
        self.print_summary()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 50)
        print("🧪 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        print("\n" + "=" * 50)

if __name__ == "__main__":
    tester = MeatSafeAPITester()
    tester.run_all_tests()