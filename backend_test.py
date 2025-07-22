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
    
    def test_checkout(self, shipping_address=None):
        """Test checkout process with enhanced shipping address"""
        if not self.auth_token:
            self.log_test("Checkout", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            params = {}
            if shipping_address:
                params["shipping_address"] = shipping_address
                
            response = self.session.post(f"{self.base_url}/cart/checkout", headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if "order_id" in data and "total" in data:
                    self.log_test("Checkout", True, f"Order placed successfully. Order ID: {data['order_id']}, Total: ${data['total']:.2f}", data)
                    return data
                else:
                    self.log_test("Checkout", False, "Invalid checkout response format", data)
                    return None
            else:
                self.log_test("Checkout", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Checkout", False, f"Request error: {str(e)}")
            return None
    
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

    # ===== ENHANCED FEATURES TESTS =====
    
    def test_product_search(self):
        """Test product search functionality"""
        try:
            # Test text search
            response = self.session.get(f"{self.base_url}/products?search=wireless")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Product Text Search", True, f"Found {len(data)} products matching 'wireless'", {"count": len(data)})
            else:
                self.log_test("Product Text Search", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            return True
        except Exception as e:
            self.log_test("Product Text Search", False, f"Request error: {str(e)}")
            return False
    
    def test_product_category_filter(self):
        """Test product category filtering"""
        try:
            response = self.session.get(f"{self.base_url}/products?category=Electronics")
            if response.status_code == 200:
                data = response.json()
                electronics_count = len(data)
                self.log_test("Product Category Filter", True, f"Found {electronics_count} Electronics products", {"count": electronics_count})
                
                # Verify all products are Electronics
                if data and all(product.get("category") == "Electronics" for product in data):
                    self.log_test("Category Filter Accuracy", True, "All returned products are Electronics")
                else:
                    self.log_test("Category Filter Accuracy", False, "Some products don't match Electronics category")
                    
                return True
            else:
                self.log_test("Product Category Filter", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Product Category Filter", False, f"Request error: {str(e)}")
            return False
    
    def test_product_price_filter(self):
        """Test product price range filtering"""
        try:
            response = self.session.get(f"{self.base_url}/products?min_price=50&max_price=200")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Product Price Filter", True, f"Found {len(data)} products in $50-$200 range", {"count": len(data)})
                
                # Verify price range
                if data:
                    prices_in_range = all(50 <= product.get("price", 0) <= 200 for product in data)
                    if prices_in_range:
                        self.log_test("Price Filter Accuracy", True, "All products within specified price range")
                    else:
                        self.log_test("Price Filter Accuracy", False, "Some products outside price range")
                        
                return True
            else:
                self.log_test("Product Price Filter", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Product Price Filter", False, f"Request error: {str(e)}")
            return False
    
    def test_product_sorting(self):
        """Test product sorting functionality"""
        try:
            # Test price sorting descending
            response = self.session.get(f"{self.base_url}/products?sort_by=price&sort_order=desc")
            if response.status_code == 200:
                data = response.json()
                if len(data) >= 2:
                    # Check if sorted by price descending
                    is_sorted = all(data[i]["price"] >= data[i+1]["price"] for i in range(len(data)-1))
                    if is_sorted:
                        self.log_test("Product Sorting", True, f"Products correctly sorted by price (desc). Range: ${data[0]['price']:.2f} - ${data[-1]['price']:.2f}")
                    else:
                        self.log_test("Product Sorting", False, "Products not properly sorted by price")
                else:
                    self.log_test("Product Sorting", True, "Sorting works (insufficient data to verify order)")
                return True
            else:
                self.log_test("Product Sorting", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Product Sorting", False, f"Request error: {str(e)}")
            return False
    
    def test_get_categories(self):
        """Test get categories endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/products/categories")
            if response.status_code == 200:
                data = response.json()
                if "categories" in data and isinstance(data["categories"], list):
                    categories = data["categories"]
                    self.log_test("Get Categories", True, f"Retrieved {len(categories)} categories: {', '.join(categories)}", data)
                    return categories
                else:
                    self.log_test("Get Categories", False, "Invalid categories response format", data)
                    return []
            else:
                self.log_test("Get Categories", False, f"HTTP {response.status_code}: {response.text}")
                return []
        except Exception as e:
            self.log_test("Get Categories", False, f"Request error: {str(e)}")
            return []
    
    def test_search_suggestions(self):
        """Test search suggestions endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/products/search/suggestions?q=smart")
            if response.status_code == 200:
                data = response.json()
                if "suggestions" in data and isinstance(data["suggestions"], list):
                    suggestions = data["suggestions"]
                    self.log_test("Search Suggestions", True, f"Retrieved {len(suggestions)} suggestions for 'smart'", data)
                    return True
                else:
                    self.log_test("Search Suggestions", False, "Invalid suggestions response format", data)
                    return False
            else:
                self.log_test("Search Suggestions", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Search Suggestions", False, f"Request error: {str(e)}")
            return False
    
    def test_profile_update(self):
        """Test profile update functionality"""
        if not self.auth_token:
            self.log_test("Profile Update", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            profile_data = {
                "name": "Sarah Johnson Updated",
                "phone": "+1-555-9999",
                "address": "456 Oak Avenue, New City, ST 54321"
            }
            
            response = self.session.put(
                f"{self.base_url}/auth/profile",
                json=profile_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Profile Update", True, "Profile updated successfully", data)
                
                # Verify update by getting profile
                profile_response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    if profile.get("name") == profile_data["name"] and profile.get("phone") == profile_data["phone"]:
                        self.log_test("Profile Update Verification", True, "Profile changes verified")
                    else:
                        self.log_test("Profile Update Verification", False, "Profile changes not reflected")
                        
                return True
            else:
                self.log_test("Profile Update", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Profile Update", False, f"Request error: {str(e)}")
            return False
    
    def test_order_history(self):
        """Test order history retrieval"""
        if not self.auth_token:
            self.log_test("Order History", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/orders", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Order History", True, f"Retrieved {len(data)} orders from history", {"order_count": len(data)})
                    return data
                else:
                    self.log_test("Order History", False, "Invalid order history format", data)
                    return []
            else:
                self.log_test("Order History", False, f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Order History", False, f"Request error: {str(e)}")
            return []
    
    def test_order_details(self, order_id):
        """Test specific order details retrieval"""
        if not self.auth_token:
            self.log_test("Order Details", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/orders/{order_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "items" in data and "total" in data:
                    self.log_test("Order Details", True, f"Retrieved order details for {order_id}. Total: ${data['total']:.2f}", data)
                    return True
                else:
                    self.log_test("Order Details", False, "Invalid order details format", data)
                    return False
            else:
                self.log_test("Order Details", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Order Details", False, f"Request error: {str(e)}")
            return False
    
    def test_user_analytics(self):
        """Test user analytics and statistics"""
        if not self.auth_token:
            self.log_test("User Analytics", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/analytics/user-stats", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["total_orders", "total_spent", "favorite_category", "average_order_value"]
                if all(field in data for field in expected_fields):
                    self.log_test("User Analytics", True, f"Analytics retrieved: {data['total_orders']} orders, ${data['total_spent']:.2f} spent, favorite: {data['favorite_category']}", data)
                    return True
                else:
                    self.log_test("User Analytics", False, "Missing analytics fields", data)
                    return False
            else:
                self.log_test("User Analytics", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("User Analytics", False, f"Request error: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Run complete test suite following the enhanced user journey"""
        print("🚀 Starting Comprehensive Enhanced Backend API Testing")
        print("=" * 70)
        
        # Test 1: Basic connectivity
        if not self.test_root_endpoint():
            print("❌ Cannot connect to API. Stopping tests.")
            return False
        
        # Test 2: Enhanced Authentication & Profile System
        print("\n🔐 Testing Enhanced Authentication & Profile System...")
        self.test_user_registration()
        if not self.test_user_login():
            print("❌ Login failed. Cannot continue with authenticated tests.")
            return False
        
        self.test_protected_endpoint()
        self.test_profile_update()
        self.test_unauthenticated_cart_access()
        
        # Test 3: Enhanced Product Management & Search
        print("\n📦 Testing Enhanced Product Management & Search...")
        self.test_initialize_products()
        products = self.test_get_products()
        
        if not products:
            print("❌ No products available. Cannot test advanced features.")
            return False
        
        # Test advanced search and filtering
        self.test_product_search()
        self.test_product_category_filter()
        self.test_product_price_filter()
        self.test_product_sorting()
        categories = self.test_get_categories()
        self.test_search_suggestions()
        
        # Test 4: Enhanced Cart System
        print("\n🛒 Testing Enhanced Cart Management...")
        self.test_get_cart()
        
        # Use first two products for testing
        product1_id = products[0]["id"]
        product2_id = products[1]["id"] if len(products) > 1 else products[0]["id"]
        
        # Add items to cart with categories
        self.test_add_to_cart(product1_id, 2)
        self.test_add_to_cart(product2_id, 1)
        
        # Update quantities
        self.test_update_cart(product1_id, 3)
        
        # Remove one item
        self.test_remove_from_cart(product2_id)
        
        # Add item back for checkout test
        self.test_add_to_cart(product1_id, 1)
        
        # Test enhanced checkout with shipping address
        print("\n📦 Testing Enhanced Checkout & Order System...")
        order_data = self.test_checkout("789 Shipping Lane, Delivery City, ST 67890")
        
        # Test 5: Order History & Tracking
        print("\n📋 Testing Order History & Tracking...")
        orders = self.test_order_history()
        
        if order_data and "order_id" in order_data:
            self.test_order_details(order_data["order_id"])
        elif orders and len(orders) > 0:
            # Test with existing order if available
            self.test_order_details(orders[0]["id"])
        
        # Test 6: Analytics System
        print("\n📊 Testing Analytics System...")
        self.test_user_analytics()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 ENHANCED TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Categorize results
        auth_tests = [r for r in self.test_results if "auth" in r["test"].lower() or "profile" in r["test"].lower() or "registration" in r["test"].lower() or "login" in r["test"].lower()]
        product_tests = [r for r in self.test_results if "product" in r["test"].lower() or "search" in r["test"].lower() or "categor" in r["test"].lower() or "sort" in r["test"].lower()]
        cart_tests = [r for r in self.test_results if "cart" in r["test"].lower() or "checkout" in r["test"].lower()]
        order_tests = [r for r in self.test_results if "order" in r["test"].lower()]
        analytics_tests = [r for r in self.test_results if "analytics" in r["test"].lower()]
        
        print(f"\n📈 Test Categories:")
        print(f"  Authentication & Profile: {sum(1 for t in auth_tests if t['success'])}/{len(auth_tests)} passed")
        print(f"  Product Management & Search: {sum(1 for t in product_tests if t['success'])}/{len(product_tests)} passed")
        print(f"  Cart Management: {sum(1 for t in cart_tests if t['success'])}/{len(cart_tests)} passed")
        print(f"  Order History: {sum(1 for t in order_tests if t['success'])}/{len(order_tests)} passed")
        print(f"  Analytics: {sum(1 for t in analytics_tests if t['success'])}/{len(analytics_tests)} passed")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        else:
            print("\n🎉 All enhanced features working perfectly!")
        
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