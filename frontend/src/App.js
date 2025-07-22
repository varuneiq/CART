import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

  const register = async (email, password, name) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { email, password, name });
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
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
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
          quantity
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

  const checkout = async () => {
    if (user && token) {
      try {
        const response = await axios.post(`${API}/cart/checkout`, {}, {
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
        message: 'Order placed successfully! (Guest checkout)'
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

// Components
const Header = () => {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  
  return (
    <header className="bg-white shadow-md">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-800">🛒 CartMart</h1>
        </div>
        
        <nav className="flex items-center space-x-6">
          <a href="/" className="text-gray-600 hover:text-gray-800">Products</a>
          <a href="/cart" className="relative text-gray-600 hover:text-gray-800">
            Cart
            {cart.items.length > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full text-xs w-5 h-5 flex items-center justify-center">
                {cart.items.reduce((sum, item) => sum + item.quantity, 0)}
              </span>
            )}
          </a>
          
          {user ? (
            <div className="flex items-center space-x-4">
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
              <a href="/login" className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
                Login
              </a>
              <a href="/register" className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded">
                Register
              </a>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
};

const ProductCard = ({ product }) => {
  const { addToCart, cartLoading } = useCart();
  
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <img 
        src={product.image_url} 
        alt={product.name}
        className="w-full h-48 object-cover"
      />
      <div className="p-4">
        <h3 className="font-semibold text-lg mb-2">{product.name}</h3>
        <p className="text-gray-600 text-sm mb-3">{product.description}</p>
        <div className="flex justify-between items-center">
          <span className="text-xl font-bold text-green-600">${product.price}</span>
          <button
            onClick={() => addToCart(product)}
            disabled={cartLoading}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {cartLoading ? 'Adding...' : 'Add to Cart'}
          </button>
        </div>
      </div>
    </div>
  );
};

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        // Initialize products if needed
        await axios.post(`${API}/init/products`);
        
        const response = await axios.get(`${API}/products`);
        setProducts(response.data);
      } catch (error) {
        console.error('Failed to load products:', error);
      }
      setLoading(false);
    };
    
    loadProducts();
  }, []);

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
};

const CartItem = ({ item }) => {
  const { updateQuantity, removeFromCart } = useCart();
  
  return (
    <div className="flex items-center space-x-4 p-4 border-b border-gray-200">
      <img 
        src={item.image_url} 
        alt={item.name}
        className="w-16 h-16 object-cover rounded"
      />
      <div className="flex-1">
        <h3 className="font-semibold">{item.name}</h3>
        <p className="text-gray-600">${item.price}</p>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
          className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
        >
          -
        </button>
        <span className="mx-2">{item.quantity}</span>
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

const CartPage = () => {
  const { cart, checkout } = useCart();
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [orderComplete, setOrderComplete] = useState(null);

  const handleCheckout = async () => {
    setCheckoutLoading(true);
    try {
      const result = await checkout();
      setOrderComplete(result);
    } catch (error) {
      console.error('Checkout failed:', error);
    }
    setCheckoutLoading(false);
  };

  if (orderComplete) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          <h2 className="text-2xl font-bold mb-2">Order Successful! 🎉</h2>
          <p>Order ID: {orderComplete.order_id}</p>
          <p>Total: ${orderComplete.total}</p>
          <p>{orderComplete.message}</p>
        </div>
        <a href="/" className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded">
          Continue Shopping
        </a>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold mb-8">Shopping Cart</h2>
      
      {cart.items.length === 0 ? (
        <div className="text-center">
          <p className="text-gray-600 text-lg mb-4">Your cart is empty</p>
          <a href="/" className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded">
            Start Shopping
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {cart.items.map(item => (
              <CartItem key={item.product_id} item={item} />
            ))}
          </div>
          
          <div className="bg-gray-50 p-6 rounded-lg h-fit">
            <h3 className="text-xl font-semibold mb-4">Order Summary</h3>
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${cart.total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping:</span>
                <span>Free</span>
              </div>
              <div className="border-t pt-2 flex justify-between font-semibold">
                <span>Total:</span>
                <span>${cart.total.toFixed(2)}</span>
              </div>
            </div>
            
            <button
              onClick={handleCheckout}
              disabled={checkoutLoading}
              className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded disabled:opacity-50"
            >
              {checkoutLoading ? 'Processing...' : 'Checkout'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const success = await login(email, password);
    if (success) {
      window.location.href = '/';
    }
    
    setLoading(false);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-md">
      <h2 className="text-3xl font-bold mb-8 text-center">Login</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
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
        Don't have an account? <a href="/register" className="text-blue-500 hover:underline">Register</a>
      </p>
    </div>
  );
};

const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const success = await register(email, password, name);
    if (success) {
      window.location.href = '/';
    }
    
    setLoading(false);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-md">
      <h2 className="text-3xl font-bold mb-8 text-center">Register</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
      
      <p className="mt-4 text-center">
        Already have an account? <a href="/login" className="text-blue-500 hover:underline">Login</a>
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
            </Routes>
          </div>
        </Router>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;