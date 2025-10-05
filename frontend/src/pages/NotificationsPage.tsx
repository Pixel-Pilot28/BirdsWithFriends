import { useState, useEffect } from 'react';
import { useMutation } from 'react-query';
import { Bell, Mail, Smartphone, Send, Check, AlertCircle } from 'lucide-react';
import { ApiService } from '@/services/api';
import { NotificationPreferences } from '@/types/api';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function NotificationsPage() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    email_notifications: false,
    webpush_notifications: false,
    sms_notifications: false,
    phone_number: '',
    story_published: true,
    episode_published: true,
    character_updates: false,
  });
  
  const [webPushSupported, setWebPushSupported] = useState(false);
  const [webPushSubscribed, setWebPushSubscribed] = useState(false);
  const [testNotificationSent, setTestNotificationSent] = useState(false);

  // Check Web Push support on mount
  useEffect(() => {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      setWebPushSupported(true);
      
      // Check if already subscribed
      navigator.serviceWorker.ready.then((registration) => {
        return registration.pushManager.getSubscription();
      }).then((subscription) => {
        setWebPushSubscribed(!!subscription);
      });
    }
  }, []);

  // Save preferences mutation
  const savePreferencesMutation = useMutation(
    (newPrefs: NotificationPreferences) => ApiService.subscribeToNotifications(newPrefs),
    {
      onSuccess: () => {
        // Preferences saved successfully - could add toast notification here
      },
    }
  );

  // Web Push subscription mutation
  const webPushMutation = useMutation(
    async () => {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        throw new Error('Web Push not supported');
      }

      const registration = await navigator.serviceWorker.ready;
      
      // Request permission
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        throw new Error('Notification permission denied');
      }

      // Subscribe to push notifications
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: 'your-vapid-public-key', // This should come from your backend
      });

      // Send subscription to server
      await ApiService.subscribeToWebPush(subscription);
      
      return subscription;
    },
    {
      onSuccess: () => {
        setWebPushSubscribed(true);
        setPreferences(prev => ({ ...prev, webpush_notifications: true }));
      },
    }
  );

  // Test notification mutation
  const testNotificationMutation = useMutation(
    () => ApiService.sendTestNotification('current-user'), // This should use actual user ID
    {
      onSuccess: () => {
        setTestNotificationSent(true);
        setTimeout(() => setTestNotificationSent(false), 3000);
      },
    }
  );

  const handlePreferenceChange = (key: keyof NotificationPreferences, value: any) => {
    const newPrefs = { ...preferences, [key]: value };
    setPreferences(newPrefs);
    savePreferencesMutation.mutate(newPrefs);
  };

  const handleWebPushToggle = async () => {
    if (!webPushSubscribed) {
      webPushMutation.mutate();
    } else {
      // Unsubscribe logic would go here
      setWebPushSubscribed(false);
      handlePreferenceChange('webpush_notifications', false);
    }
  };

  const handleTestNotification = () => {
    testNotificationMutation.mutate();
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-gray-900">Notifications</h1>
        <p className="text-gray-600 mt-1">
          Configure how you'd like to be notified about bird stories and updates
        </p>
      </div>

      {/* Notification Methods */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Email Notifications */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Mail className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Email Notifications</h3>
              <p className="text-sm text-gray-600">Get notified via email</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Enable email notifications</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.email_notifications}
                  onChange={(e) => handlePreferenceChange('email_notifications', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {preferences.email_notifications && (
              <div className="pl-4 border-l-2 border-blue-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">New stories published</span>
                  <input
                    type="checkbox"
                    checked={preferences.story_published}
                    onChange={(e) => handlePreferenceChange('story_published', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">New episodes published</span>
                  <input
                    type="checkbox"
                    checked={preferences.episode_published}
                    onChange={(e) => handlePreferenceChange('episode_published', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Character updates</span>
                  <input
                    type="checkbox"
                    checked={preferences.character_updates}
                    onChange={(e) => handlePreferenceChange('character_updates', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Web Push Notifications */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Bell className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Web Push Notifications</h3>
              <p className="text-sm text-gray-600">Instant browser notifications</p>
            </div>
          </div>

          {!webPushSupported ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-yellow-600" />
                <span className="text-sm text-yellow-800">
                  Web Push notifications are not supported in your browser
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  {webPushSubscribed ? 'Subscribed to push notifications' : 'Enable push notifications'}
                </span>
                <button
                  onClick={handleWebPushToggle}
                  disabled={webPushMutation.isLoading}
                  className={`btn text-sm ${
                    webPushSubscribed 
                      ? 'bg-green-600 text-white hover:bg-green-700' 
                      : 'btn-primary'
                  }`}
                >
                  {webPushMutation.isLoading ? (
                    <LoadingSpinner size="sm" />
                  ) : webPushSubscribed ? (
                    <>
                      <Check className="w-4 h-4 mr-1" />
                      Subscribed
                    </>
                  ) : (
                    'Subscribe'
                  )}
                </button>
              </div>

              {webPushSubscribed && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <Check className="w-5 h-5 text-green-600" />
                    <span className="text-sm text-green-800">
                      You'll receive push notifications for new stories and episodes
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* SMS Notifications (Future Feature) */}
        <div className="card p-6 opacity-75">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">SMS Notifications</h3>
              <p className="text-sm text-gray-600">Get text messages (coming soon)</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="form-label">Phone Number</label>
              <input
                type="tel"
                value={preferences.phone_number || ''}
                onChange={(e) => handlePreferenceChange('phone_number', e.target.value)}
                className="form-input"
                placeholder="+1 (555) 123-4567"
                disabled
              />
              <p className="text-xs text-gray-500 mt-1">SMS notifications coming in a future update</p>
            </div>
          </div>
        </div>

        {/* Test Notifications */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <Send className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Test Notifications</h3>
              <p className="text-sm text-gray-600">Send a test notification</p>
            </div>
          </div>

          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Send a test notification to verify your settings are working correctly.
            </p>
            
            <button
              onClick={handleTestNotification}
              disabled={testNotificationMutation.isLoading || testNotificationSent}
              className="btn-secondary w-full flex items-center justify-center space-x-2"
            >
              {testNotificationMutation.isLoading ? (
                <LoadingSpinner size="sm" />
              ) : testNotificationSent ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Test Sent!</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Send Test Notification</span>
                </>
              )}
            </button>

            {testNotificationSent && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <p className="text-sm text-green-800">
                  Test notification sent! Check your email and browser notifications.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Notification History (Future Feature) */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification History</h3>
        <div className="text-center py-8 text-gray-500">
          <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Notification history will appear here</p>
          <p className="text-xs text-gray-400 mt-1">Coming in a future update</p>
        </div>
      </div>
    </div>
  );
}