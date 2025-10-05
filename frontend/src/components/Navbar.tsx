import { Link, useLocation } from 'react-router-dom';
import { Camera, Users, Bell, BookOpen } from 'lucide-react';
import { clsx } from 'clsx';

const navigation = [
  { name: 'Live Feed', href: '/', icon: Camera },
  { name: 'Stories', href: '/stories', icon: BookOpen },
  { name: 'Characters', href: '/characters', icon: Users },
  { name: 'Notifications', href: '/notifications', icon: Bell },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
              <Camera className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-semibold text-xl text-gray-900">
              Birds with Friends
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex space-x-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}