#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Cart Management System
Tests authentication, product management, and cart functionality
"""

import requests
import json
import sys
from datetime import datetime

# Get backend URL from frontend .env
BACKEND_URL = "https://124225a6-c395-4af1-9058-0bc32327ad52.preview.emergentagent.com/api"

class CartSystemTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.user_data = {
            "email": "sarah.johnson@example.com",
            "password": "SecurePass123!",
            "name": "Sarah Johnson",
            "phone": "+1-555-0123",
            "address": "123 Main Street, Anytown, ST 12345"
        }
        self.test_results = []
        
    def log_test(self, test_name, success, message, response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
        
    def test_root_endpoint(self):
        """Test basic API connectivity"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Root Endpoint", True, f"API accessible: {data.get('message', 'OK')}")
                return True
            else:
                self.log_test("API Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("API Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=self.user_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "token_type" in data:
                    self.auth_token = data["access_token"]
                    self.log_test("User Registration", True, "User registered successfully with JWT token", data)
                    return True
                else:
                    self.log_test("User Registration", False, "Missing token in response", data)
                    return False
            elif response.status_code == 400 and "already registered" in response.text:
                self.log_test("User Registration", True, "User already exists (expected for repeat tests)")
                return True
            else:
                self.log_test("User Registration", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("User Registration", False, f"Request error: {str(e)}")
            return False
    
    def test_user_login(self):
        """Test user login endpoint"""
        try:
            login_data = {
                "email": self.user_data["email"],
                "password": self.user_data["password"]
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "token_type" in data:
                    self.auth_token = data["access_token"]
                    self.log_test("User Login", True, "Login successful with JWT token", data)
                    return True
                else:
                    self.log_test("User Login", False, "Missing token in response", data)
                    return False
            else:
                self.log_test("User Login", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("User Login", False, f"Request error: {str(e)}")
            return False
    
    def test_protected_endpoint(self):
        """Test protected /auth/me endpoint"""
        if not self.auth_token:
            self.log_test("Protected Endpoint", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "email" in data and "name" in data:
                    self.log_test("Protected Endpoint", True, f"User profile retrieved: {data['name']}", data)
                    return True
                else:
                    self.log_test("Protected Endpoint", False, "Invalid user data format", data)
                    return False
            else:
                self.log_test("Protected Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Protected Endpoint", False, f"Request error: {str(e)}")
            return False
    
    def test_initialize_products(self):
        """Test product initialization endpoint"""
        try:
            response = self.session.post(f"{self.base_url}/init/products")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Initialize Products", True, f"Products initialized: {data.get('message', 'OK')}", data)
                return True
            else:
                self.log_test("Initialize Products", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Initialize Products", False, f"Request error: {str(e)}")
            return False
    
    def test_get_products(self):
        """Test get products endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/products")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.log_test("Get Products", True, f"Retrieved {len(data)} products", {"count": len(data), "first_product": data[0] if data else None})
                    return data
                else:
                    self.log_test("Get Products", False, "No products found or invalid format", data)
                    return []
            else:
                self.log_test("Get Products", False, f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Get Products", False, f"Request error: {str(e)}")
            return []
    
    def test_get_cart(self):
        """Test get cart endpoint (requires authentication)"""
        if not self.auth_token:
            self.log_test("Get Cart", False, "No auth token available")
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/cart", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Get Cart", True, f"Cart retrieved with {len(data.get('items', []))} items", data)
                return data
            else:
                self.log_test("Get Cart", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Get Cart", False, f"Request error: {str(e)}")
            return None
    
    def test_add_to_cart(self, product_id, quantity=2):
        """Test add to cart endpoint"""
        if not self.auth_token:
            self.log_test("Add to Cart", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            params = {"product_id": product_id, "quantity": quantity}
            
            response = self.session.post(
                f"{self.base_url}/cart/add",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Add to Cart", True, f"Added {quantity} items to cart. Total: ${data.get('total', 0):.2f}", data)
                return True
            else:
                self.log_test("Add to Cart", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Add to Cart", False, f"Request error: {str(e)}")
            return False
    
    def test_update_cart(self, product_id, new_quantity=1):
        """Test update cart item quantity"""
        if not self.auth_token:
            self.log_test("Update Cart", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            params = {"product_id": product_id, "quantity": new_quantity}
            
            response = self.session.put(
                f"{self.base_url}/cart/update",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Update Cart", True, f"Updated quantity to {new_quantity}. Total: ${data.get('total', 0):.2f}", data)
                return True
            else:
                self.log_test("Update Cart", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Update Cart", False, f"Request error: {str(e)}")
            return False
    
    def test_remove_from_cart(self, product_id):
        """Test remove item from cart"""
        if not self.auth_token:
            self.log_test("Remove from Cart", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.delete(
                f"{self.base_url}/cart/remove/{product_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Remove from Cart", True, f"Item removed. Total: ${data.get('total', 0):.2f}", data)
                return True
            else:
                self.log_test("Remove from Cart", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Remove from Cart", False, f"Request error: {str(e)}")
            return False
    
    def test_checkout(self):
        """Test checkout process"""
        if not self.auth_token:
            self.log_test("Checkout", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.post(f"{self.base_url}/cart/checkout", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "order_id" in data and "total" in data:
                    self.log_test("Checkout", True, f"Order placed successfully. Order ID: {data['order_id']}, Total: ${data['total']:.2f}", data)
                    return True
                else:
                    self.log_test("Checkout", False, "Invalid checkout response format", data)
                    return False
            else:
                self.log_test("Checkout", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Checkout", False, f"Request error: {str(e)}")
            return False
    
    def test_unauthenticated_cart_access(self):
        """Test that cart endpoints require authentication"""
        try:
            # Test without auth header
            response = self.session.get(f"{self.base_url}/cart")
            
            if response.status_code == 401 or response.status_code == 403:
                self.log_test("Unauthenticated Cart Access", True, "Cart properly protected - requires authentication")
                return True
            else:
                self.log_test("Unauthenticated Cart Access", False, f"Cart not properly protected. HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Unauthenticated Cart Access", False, f"Request error: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Run complete test suite following the user journey"""
        print("🚀 Starting Comprehensive Backend API Testing")
        print("=" * 60)
        
        # Test 1: Basic connectivity
        if not self.test_root_endpoint():
            print("❌ Cannot connect to API. Stopping tests.")
            return False
        
        # Test 2: Authentication flow
        print("\n🔐 Testing Authentication System...")
        self.test_user_registration()
        if not self.test_user_login():
            print("❌ Login failed. Cannot continue with authenticated tests.")
            return False
        
        self.test_protected_endpoint()
        self.test_unauthenticated_cart_access()
        
        # Test 3: Product management
        print("\n📦 Testing Product Management...")
        self.test_initialize_products()
        products = self.test_get_products()
        
        if not products:
            print("❌ No products available. Cannot test cart functionality.")
            return False
        
        # Test 4: Cart functionality (complete user journey)
        print("\n🛒 Testing Cart Management...")
        self.test_get_cart()
        
        # Use first two products for testing
        product1_id = products[0]["id"]
        product2_id = products[1]["id"] if len(products) > 1 else products[0]["id"]
        
        # Add items to cart
        self.test_add_to_cart(product1_id, 2)
        self.test_add_to_cart(product2_id, 1)
        
        # Update quantities
        self.test_update_cart(product1_id, 3)
        
        # Remove one item
        self.test_remove_from_cart(product2_id)
        
        # Add item back for checkout test
        self.test_add_to_cart(product1_id, 1)
        
        # Test checkout
        self.test_checkout()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        return passed == total

def main():
    """Main test execution"""
    tester = CartSystemTester()
    success = tester.run_comprehensive_test()
    
    # Save detailed results
    with open("/app/backend_test_results.json", "w") as f:
        json.dump(tester.test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    if success:
        print("\n🎉 All backend tests passed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the results above.")
        sys.exit(1)

if __name__ == "__main__":
    main()