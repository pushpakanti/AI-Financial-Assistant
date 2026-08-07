import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Mail, Calendar, Shield, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export const Profile: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6 text-left">
      <div>
        <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
          User Profile
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Review your personal profile settings and credentials.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full"
      >
        <Card className="overflow-hidden relative">
          {/* Accent header */}
          <div className="absolute top-0 left-0 w-full h-2.5 bg-indigo-650" />
          
          <CardContent className="p-8 pt-10 flex flex-col gap-6">
            <div className="flex items-center gap-4 border-b border-slate-150 dark:border-slate-800 pb-6">
              <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-2xl shadow-inner select-none">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col gap-0.5">
                <h3 className="text-lg font-black text-slate-800 dark:text-slate-100">
                  {user.full_name}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="success" className="text-[9px] uppercase">
                    Active Account
                  </Badge>
                  <span className="text-xs text-slate-400 font-semibold">
                    ID: #{user.id}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-50 dark:bg-slate-900/50 rounded-xl text-slate-400">
                  <Mail className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Email Address</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5">{user.email}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-50 dark:bg-slate-900/50 rounded-xl text-slate-400">
                  <Calendar className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Member Since</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5">
                    {new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 col-span-1 sm:col-span-2">
                <div className="p-2.5 bg-slate-50 dark:bg-slate-900/50 rounded-xl text-slate-400">
                  <Shield className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Access Scope</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5 flex items-center gap-1.5">
                    Authorized User <Sparkles className="w-4 h-4 text-indigo-500" />
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};
export default Profile;
