import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginForm } from './components/LoginForm';
import { AdminDashboard } from './components/AdminDashboard';
import { TenantDashboard } from './components/TenantDashboard';
import { CourseRegistrationForm } from './components/CourseRegistrationForm';
import { OnboardingWizard } from './components/OnboardingWizard';

const AppContent: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [showRegistration, setShowRegistration] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (showRegistration) {
    return (
      <CourseRegistrationForm
        onSuccess={() => {
          setShowRegistration(false);
          setShowOnboarding(true);
        }}
        onBackToLogin={() => setShowRegistration(false)}
      />
    );
  }

  if (showOnboarding) {
    return (
      <OnboardingWizard
        onComplete={() => setShowOnboarding(false)}
      />
    );
  }

  if (!user) {
    return <LoginForm onShowRegistration={() => setShowRegistration(true)} />;
  }

  if (user.role === 'super_admin' || user.role === 'regional_admin' || user.role === 'course_manager') {
    return <AdminDashboard />;
  }

  return <TenantDashboard />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
