import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      
      // Get user info
      const userResponse = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      setUser(userResponse.data);
      
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const register = async (email, password, name, phone, address) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { 
        email, password, name, phone, address 
      });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      
      // Get user info
      const userResponse = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      setUser(userResponse.data);
      
      return true;
    } catch (error) {
      console.error('Registration failed:', error);
      return false;
    }
  };

  const updateProfile = async (profileData) => {
    try {
      await axios.put(`${API}/auth/profile`, profileData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh user info
      const userResponse = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(userResponse.data);
      
      return true;
    } catch (error) {
      console.error('Profile update failed:', error);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  };

  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(response.data);
        } catch (error) {
          logout();
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, login, register, updateProfile, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Cart Context
const CartContext = createContext();

const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};

const CartProvider = ({ children }) => {
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [cartLoading, setCartLoading] = useState(false);
  const { user, token } = useAuth();

  // Load cart from localStorage for guests or API for logged users
  const loadCart = async () => {
    if (user && token) {
      try {
        const response = await axios.get(`${API}/cart`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCart(response.data);
      } catch (error) {
        console.error('Failed to load cart:', error);
      }
    } else {
      const savedCart = localStorage.getItem('guestCart');
      if (savedCart) {
        setCart(JSON.parse(savedCart));
      }
    }
  };

  // Save guest cart to localStorage
  const saveGuestCart = (cartData) => {
    localStorage.setItem('guestCart', JSON.stringify(cartData));
  };

  const addToCart = async (product, quantity = 1) => {
    setCartLoading(true);
    
    if (user && token) {
      try {
        const response = await axios.post(`${API}/cart/add?product_id=${product.id}&quantity=${quantity}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCart(response.data);
      } catch (error) {
        console.error('Failed to add to cart:', error);
      }
    } else {
      // Guest cart management
      const newCart = { ...cart };
      const existingItem = newCart.items.find(item => item.product_id === product.id);
      
      if (existingItem) {
        existingItem.quantity += quantity;
      } else {
        newCart.items.push({
          product_id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          quantity,
          category: product.category
        });
      }
      
      newCart.total = newCart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      setCart(newCart);
      saveGuestCart(newCart);
    }
    
    setCartLoading(false);
  };

  const updateQuantity = async (productId, quantity) => {
    setCartLoading(true);
    
    if (user && token) {
      try {
        const response = await axios.put(`${API}/cart/update?product_id=${productId}&quantity=${quantity}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCart(response.data);
      } catch (error) {
        console.error('Failed to update cart:', error);
      }
    } else {
      const newCart = { ...cart };
      if (quantity <= 0) {
        newCart.items = newCart.items.filter(item => item.product_id !== productId);
      } else {
        const item = newCart.items.find(item => item.product_id === productId);
        if (item) {
          item.quantity = quantity;
        }
      }
      
      newCart.total = newCart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      setCart(newCart);
      saveGuestCart(newCart);
    }
    
    setCartLoading(false);
  };

  const removeFromCart = async (productId) => {
    setCartLoading(true);
    
    if (user && token) {
      try {
        const response = await axios.delete(`${API}/cart/remove/${productId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCart(response.data);
      } catch (error) {
        console.error('Failed to remove from cart:', error);
      }
    } else {
      const newCart = { ...cart };
      newCart.items = newCart.items.filter(item => item.product_id !== productId);
      newCart.total = newCart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      setCart(newCart);
      saveGuestCart(newCart);
    }
    
    setCartLoading(false);
  };

  const checkout = async (shippingAddress) => {
    if (user && token) {
      try {
        const response = await axios.post(`${API}/cart/checkout?shipping_address=${encodeURIComponent(shippingAddress || '')}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCart({ items: [], total: 0 });
        return response.data;
      } catch (error) {
        console.error('Checkout failed:', error);
        throw error;
      }
    } else {
      // Mock checkout for guests
      const orderData = {
        order_id: 'guest-' + Date.now(),
        total: cart.total,
        message: 'Order placed successfully! (Guest checkout)',
        order_date: new Date().toISOString()
      };
      setCart({ items: [], total: 0 });
      localStorage.removeItem('guestCart');
      return orderData;
    }
  };

  useEffect(() => {
    loadCart();
  }, [user, token]);

  return (
    <CartContext.Provider value={{
      cart,
      cartLoading,
      addToCart,
      updateQuantity,
      removeFromCart,
      checkout,
      loadCart
    }}>
      {children}
    </CartContext.Provider>
  );
};

// Enhanced Header Component
const Header = () => {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const navigate = useNavigate();
  
  return (
    <header className="bg-white shadow-md sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/')} className="text-2xl font-bold text-gray-800 hover:text-blue-600">
            🛒 CartMart
          </button>
        </div>
        
        <nav className="flex items-center space-x-6">
          <button onClick={() => navigate('/')} className="text-gray-600 hover:text-gray-800">
            Products
          </button>
          <button onClick={() => navigate('/cart')} className="relative text-gray-600 hover:text-gray-800">
            Cart
            {cart.items.length > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full text-xs w-5 h-5 flex items-center justify-center">
                {cart.items.reduce((sum, item) => sum + item.quantity, 0)}
              </span>
            )}
          </button>
          
          {user ? (
            <div className="flex items-center space-x-4">
              <button onClick={() => navigate('/orders')} className="text-gray-600 hover:text-gray-800">
                Orders
              </button>
              <button onClick={() => navigate('/profile')} className="text-gray-600 hover:text-gray-800">
                Profile
              </button>
              <span className="text-gray-600">Hello, {user.name}</span>
              <button 
                onClick={logout}
                className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="space-x-2">
              <button onClick={() => navigate('/login')} className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
                Login
              </button>
              <button onClick={() => navigate('/register')} className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded">
                Register
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
};

// Enhanced Search and Filter Component
const SearchAndFilter = ({ onSearch, onFilter, categories }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [priceRange, setPriceRange] = useState({ min: '', max: '' });
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  const handleSearch = () => {
    onSearch({
      search: searchTerm,
      category: selectedCategory,
      min_price: priceRange.min ? parseFloat(priceRange.min) : null,
      max_price: priceRange.max ? parseFloat(priceRange.max) : null,
      sort_by: sortBy,
      sort_order: sortOrder
    });
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedCategory('');
    setPriceRange({ min: '', max: '' });
    setSortBy('name');
    setSortOrder('asc');
    onSearch({});
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Search */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search products..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>

        {/* Category Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>

        {/* Price Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Price Range</label>
          <div className="flex space-x-2">
            <input
              type="number"
              value={priceRange.min}
              onChange={(e) => setPriceRange({...priceRange, min: e.target.value})}
              placeholder="Min"
              className="w-full px-2 py-2 border border-gray-300 rounded-md text-sm"
            />
            <input
              type="number"
              value={priceRange.max}
              onChange={(e) => setPriceRange({...priceRange, max: e.target.value})}
              placeholder="Max"
              className="w-full px-2 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
        </div>

        {/* Sort By */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="name">Name</option>
            <option value="price">Price</option>
            <option value="rating">Rating</option>
            <option value="created_at">Newest</option>
          </select>
        </div>

        {/* Sort Order */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Order</label>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
      </div>

      <div className="flex justify-center space-x-4 mt-4">
        <button
          onClick={handleSearch}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded"
        >
          Apply Filters
        </button>
        <button
          onClick={clearFilters}
          className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
};

// Enhanced Product Card
const ProductCard = ({ product }) => {
  const { addToCart, cartLoading } = useCart();
  
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow product-card">
      <img 
        src={product.image_url} 
        alt={product.name}
        className="w-full h-48 object-cover"
      />
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-lg">{product.name}</h3>
          <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">{product.category}</span>
        </div>
        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{product.description}</p>
        
        <div className="flex items-center mb-3">
          <div className="flex text-yellow-400">
            {'★'.repeat(Math.floor(product.rating))}{'☆'.repeat(5-Math.floor(product.rating))}
          </div>
          <span className="text-sm text-gray-600 ml-2">({product.reviews_count})</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-xl font-bold text-green-600">₹{product.price.toLocaleString('en-IN')}</span>
          <button
            onClick={() => addToCart(product)}
            disabled={cartLoading}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {cartLoading ? 'Adding...' : 'Add to Cart'}
          </button>
        </div>
        
        <div className="mt-2 text-xs text-gray-500">
          Stock: {product.stock} available
        </div>
      </div>
    </div>
  );
};

// Enhanced Product List
const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentFilters, setCurrentFilters] = useState({});

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API}/products/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const loadProducts = async (filters = {}) => {
    setLoading(true);
    try {
      // Initialize products if needed
      await axios.post(`${API}/init/products`);
      
      const params = new URLSearchParams();
      Object.keys(filters).forEach(key => {
        if (filters[key] !== null && filters[key] !== '') {
          params.append(key, filters[key]);
        }
      });
      
      const response = await axios.get(`${API}/products?${params.toString()}`);
      setProducts(response.data);
      setCurrentFilters(filters);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadCategories();
    loadProducts();
  }, []);

  const handleSearch = (filters) => {
    loadProducts(filters);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold mb-8 text-center">Featured Products</h2>
      
      <SearchAndFilter 
        onSearch={handleSearch}
        categories={categories}
      />
      
      {products.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">No products found matching your criteria.</p>
          <button 
            onClick={() => handleSearch({})}
            className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded"
          >
            Show All Products
          </button>
        </div>
      ) : (
        <>
          <div className="mb-4 text-gray-600">
            Showing {products.length} products
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {products.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

// Enhanced Cart Item Component
const CartItem = ({ item }) => {
  const { updateQuantity, removeFromCart } = useCart();
  
  return (
    <div className="flex items-center space-x-4 p-4 border-b border-gray-200 cart-item">
      <img 
        src={item.image_url} 
        alt={item.name}
        className="w-16 h-16 object-cover rounded"
      />
      <div className="flex-1">
        <h3 className="font-semibold">{item.name}</h3>
        <p className="text-gray-600">${item.price}</p>
        <span className="text-xs bg-gray-100 px-2 py-1 rounded">{item.category}</span>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
          className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
        >
          -
        </button>
        <span className="mx-2 min-w-8 text-center">{item.quantity}</span>
        <button
          onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
          className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
        >
          +
        </button>
      </div>
      <div className="text-right">
        <p className="font-semibold">${(item.price * item.quantity).toFixed(2)}</p>
        <button
          onClick={() => removeFromCart(item.product_id)}
          className="text-red-500 hover:text-red-600 text-sm"
        >
          Remove
        </button>
      </div>
    </div>
  );
};

// Enhanced Cart Page
const CartPage = () => {
  const { cart, checkout } = useCart();
  const { user } = useAuth();
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [orderComplete, setOrderComplete] = useState(null);
  const [shippingAddress, setShippingAddress] = useState('');

  const handleCheckout = async () => {
    setCheckoutLoading(true);
    try {
      const result = await checkout(shippingAddress);
      setOrderComplete(result);
    } catch (error) {
      console.error('Checkout failed:', error);
    }
    setCheckoutLoading(false);
  };

  // Group items by category for better organization
  const itemsByCategory = cart.items.reduce((acc, item) => {
    const category = item.category || 'Other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(item);
    return acc;
  }, {});

  if (orderComplete) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <div className="bg-green-100 border border-green-400 text-green-700 px-6 py-4 rounded-lg mb-6">
          <h2 className="text-2xl font-bold mb-2">🎉 Order Successful!</h2>
          <p className="text-lg">Order ID: <span className="font-mono">{orderComplete.order_id}</span></p>
          <p>Total: <span className="font-bold">${orderComplete.total}</span></p>
          <p className="text-sm mt-2">{orderComplete.message}</p>
          <p className="text-xs text-gray-600 mt-1">
            Order Date: {new Date(orderComplete.order_date).toLocaleString()}
          </p>
        </div>
        <button 
          onClick={() => window.location.href = '/'}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded mr-4"
        >
          Continue Shopping
        </button>
        {user && (
          <button 
            onClick={() => window.location.href = '/orders'}
            className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded"
          >
            View Orders
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold mb-8">Shopping Cart</h2>
      
      {cart.items.length === 0 ? (
        <div className="text-center">
          <div className="text-6xl mb-4">🛒</div>
          <p className="text-gray-600 text-lg mb-4">Your cart is empty</p>
          <button 
            onClick={() => window.location.href = '/'}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded"
          >
            Start Shopping
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {Object.keys(itemsByCategory).map(category => (
              <div key={category} className="mb-6">
                <h3 className="text-lg font-semibold mb-3 text-gray-700 border-b pb-2">
                  {category}
                </h3>
                {itemsByCategory[category].map(item => (
                  <CartItem key={item.product_id} item={item} />
                ))}
              </div>
            ))}
          </div>
          
          <div className="bg-gray-50 p-6 rounded-lg h-fit">
            <h3 className="text-xl font-semibold mb-4">Order Summary</h3>
            
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span>Items ({cart.items.reduce((sum, item) => sum + item.quantity, 0)}):</span>
                <span>${cart.total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping:</span>
                <span className="text-green-600">Free</span>
              </div>
              <div className="flex justify-between">
                <span>Tax:</span>
                <span>${(cart.total * 0.08).toFixed(2)}</span>
              </div>
              <div className="border-t pt-2 flex justify-between font-semibold text-lg">
                <span>Total:</span>
                <span>${(cart.total * 1.08).toFixed(2)}</span>
              </div>
            </div>

            {user && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Shipping Address (Optional)
                </label>
                <textarea
                  value={shippingAddress}
                  onChange={(e) => setShippingAddress(e.target.value)}
                  placeholder={user.address || "Enter shipping address..."}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  rows={3}
                />
              </div>
            )}
            
            <button
              onClick={handleCheckout}
              disabled={checkoutLoading}
              className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded disabled:opacity-50"
            >
              {checkoutLoading ? 'Processing...' : 'Proceed to Checkout'}
            </button>
            
            {!user && (
              <p className="text-xs text-gray-600 mt-2 text-center">
                Note: This is a guest checkout. Sign up to track your orders!
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// User Profile Page
const ProfilePage = () => {
  const { user, updateProfile } = useAuth();
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    phone: user?.phone || '',
    address: user?.address || ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [userStats, setUserStats] = useState(null);

  useEffect(() => {
    if (user) {
      setProfileData({
        name: user.name || '',
        phone: user.phone || '',
        address: user.address || ''
      });
      
      // Load user statistics
      const loadStats = async () => {
        try {
          const response = await axios.get(`${API}/analytics/user-stats`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
          });
          setUserStats(response.data);
        } catch (error) {
          console.error('Failed to load user stats:', error);
        }
      };
      
      loadStats();
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    
    const success = await updateProfile(profileData);
    if (success) {
      setMessage('Profile updated successfully!');
    } else {
      setMessage('Failed to update profile. Please try again.');
    }
    
    setLoading(false);
    
    // Clear message after 3 seconds
    setTimeout(() => setMessage(''), 3000);
  };

  if (!user) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <p>Please log in to view your profile.</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h2 className="text-3xl font-bold mb-8">My Profile</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Profile Form */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-semibold mb-4">Personal Information</h3>
          
          {message && (
            <div className={`p-3 rounded mb-4 ${
              message.includes('successfully') 
                ? 'bg-green-100 text-green-700 border border-green-200' 
                : 'bg-red-100 text-red-700 border border-red-200'
            }`}>
              {message}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100"
              />
              <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input
                type="text"
                value={profileData.name}
                onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="tel"
                value={profileData.phone}
                onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="(555) 123-4567"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <textarea
                value={profileData.address}
                onChange={(e) => setProfileData({...profileData, address: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                rows={3}
                placeholder="123 Main St, City, State 12345"
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded disabled:opacity-50"
            >
              {loading ? 'Updating...' : 'Update Profile'}
            </button>
          </form>
        </div>

        {/* User Statistics */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-semibold mb-4">Account Statistics</h3>
          
          {userStats ? (
            <div className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-800">Total Orders</h4>
                <p className="text-2xl font-bold text-blue-600">{userStats.total_orders}</p>
              </div>
              
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="font-semibold text-green-800">Total Spent</h4>
                <p className="text-2xl font-bold text-green-600">${userStats.total_spent}</p>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-semibold text-purple-800">Average Order</h4>
                <p className="text-2xl font-bold text-purple-600">${userStats.average_order_value}</p>
              </div>
              
              {userStats.favorite_category && (
                <div className="bg-orange-50 p-4 rounded-lg">
                  <h4 className="font-semibold text-orange-800">Favorite Category</h4>
                  <p className="text-2xl font-bold text-orange-600">{userStats.favorite_category}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500">
              <p>Loading statistics...</p>
            </div>
          )}
          
          <div className="mt-6 text-sm text-gray-600">
            <p><strong>Account created:</strong> {new Date(user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Order History Page
const OrderHistoryPage = () => {
  const { user, token } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => {
    if (user && token) {
      loadOrders();
    }
  }, [user, token]);

  const loadOrders = async () => {
    try {
      const response = await axios.get(`${API}/orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrders(response.data);
    } catch (error) {
      console.error('Failed to load orders:', error);
    }
    setLoading(false);
  };

  if (!user) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <p>Please log in to view your order history.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold mb-8">Order History</h2>
      
      {orders.length === 0 ? (
        <div className="text-center">
          <div className="text-6xl mb-4">📦</div>
          <p className="text-gray-600 text-lg mb-4">No orders found</p>
          <button 
            onClick={() => window.location.href = '/'}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded"
          >
            Start Shopping
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(order => (
            <div key={order.id} className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-lg">Order #{order.id.slice(0, 8)}</h3>
                  <p className="text-gray-600">
                    {new Date(order.order_date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">${order.total.toFixed(2)}</p>
                  <span className={`px-2 py-1 rounded-full text-sm ${
                    order.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                  </span>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">Items ({order.items.length}):</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {order.items.map((item, index) => (
                    <div key={index} className="flex items-center space-x-3 bg-gray-50 p-3 rounded">
                      <img 
                        src={item.image_url} 
                        alt={item.name}
                        className="w-12 h-12 object-cover rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.name}</p>
                        <p className="text-xs text-gray-600">Qty: {item.quantity} × ${item.price}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {order.shipping_address && (
                <div className="mt-4 text-sm text-gray-600">
                  <strong>Shipping Address:</strong> {order.shipping_address}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Enhanced Login Page
const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    const success = await login(email, password);
    if (success) {
      navigate('/');
    } else {
      setError('Invalid email or password. Please try again.');
    }
    
    setLoading(false);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-md">
      <h2 className="text-3xl font-bold mb-8 text-center">Welcome Back</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      
      <p className="mt-4 text-center">
        Don't have an account? <button onClick={() => navigate('/register')} className="text-blue-500 hover:underline">Register</button>
      </p>
    </div>
  );
};

// Enhanced Register Page
const RegisterPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    address: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    const success = await register(
      formData.email, 
      formData.password, 
      formData.name, 
      formData.phone, 
      formData.address
    );
    
    if (success) {
      navigate('/');
    } else {
      setError('Registration failed. Please try again.');
    }
    
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-md">
      <h2 className="text-3xl font-bold mb-8 text-center">Create Account</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            placeholder="(555) 123-4567"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
          <textarea
            name="address"
            value={formData.address}
            onChange={handleChange}
            placeholder="123 Main St, City, State 12345"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            rows={3}
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Creating Account...' : 'Create Account'}
        </button>
      </form>
      
      <p className="mt-4 text-center">
        Already have an account? <button onClick={() => navigate('/login')} className="text-blue-500 hover:underline">Login</button>
      </p>
    </div>
  );
};

// Main App component
function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Header />
            
            <Routes>
              <Route path="/" element={<ProductList />} />
              <Route path="/cart" element={<CartPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/orders" element={<OrderHistoryPage />} />
            </Routes>
          </div>
        </Router>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;