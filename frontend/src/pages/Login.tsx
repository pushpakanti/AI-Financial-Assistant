import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Mail, Lock, User, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

import { Logo } from '../components/ui/Logo';

export const Login: React.FC = () => {
  const { login, register } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || (isRegister && !fullName)) {
      showToast('Please fill in all fields', 'info');
      return;
    }

    if (password.length < 8) {
      showToast('Password must be at least 8 characters long', 'info');
      return;
    }

    setIsLoading(true);
    try {
      if (isRegister) {
        await register(email, password, fullName);
        showToast('Account created! Logging you in...', 'success');
        // Automatically log in after registration
        await login(email, password);
      } else {
        await login(email, password);
        showToast('Welcome back!', 'success');
      }
      navigate('/dashboard');
    } catch (err: any) {
      console.error(err);
      showToast(err.message || 'Authentication failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4 relative overflow-hidden transition-colors duration-250">
      {/* Background Orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-400/20 dark:bg-indigo-900/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-400/20 dark:bg-purple-900/10 rounded-full blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md rounded-3xl glass-card p-8 border border-slate-200/50 dark:border-slate-800/50 shadow-2xl relative z-10"
      >
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="w-12 h-12 rounded-2xl bg-indigo-650 flex items-center justify-center text-white mx-auto shadow-lg shadow-indigo-600/25 mb-4 p-2">
            <Logo className="w-full h-full" />
          </div>
          <h2 className="text-2xl font-extrabold text-slate-850 dark:text-slate-100 flex items-center justify-center gap-1.5">
            <span className="text-indigo-500">✦</span> FinMate Copilot
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 font-medium">
            Your AI Financial Companion
          </p>
          <div className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-150/30 dark:border-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-bold uppercase tracking-wider">
            {isRegister ? 'Create Account' : 'Sign In'}
            <Sparkles className="w-3.5 h-3.5" />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {isRegister && (
            <Input
              label="Full Name"
              type="text"
              placeholder="John Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              leftIcon={<User className="w-4 h-4" />}
              required
            />
          )}

          <Input
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="w-4 h-4" />}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            leftIcon={<Lock className="w-4 h-4" />}
            required
          />

          <Button type="submit" isLoading={isLoading} className="w-full mt-2">
            {isRegister ? 'Create Account' : 'Sign In'}
          </Button>
        </form>

        <div className="mt-6 text-center border-t border-slate-150 dark:border-slate-800/60 pt-5">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              // reset fields
              setEmail('');
              setPassword('');
              setFullName('');
            }}
            className="text-sm font-semibold text-indigo-650 dark:text-indigo-400 hover:underline transition-all duration-200"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};
export default Login;
