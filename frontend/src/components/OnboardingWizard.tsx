import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { CheckCircle, Monitor, Users, CreditCard, Rocket } from 'lucide-react';

interface OnboardingWizardProps {
  onComplete: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const steps = [
    {
      id: 0,
      title: 'Welcome to Golf CMS',
      description: 'Let\'s get your course set up with digital tee box displays',
      icon: Rocket,
      content: (
        <div className="space-y-4">
          <p className="text-gray-600">
            Welcome to Golf CMS! We'll help you set up your digital tee box display system in just a few steps.
          </p>
          <div className="bg-blue-50 p-4 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">What you'll accomplish:</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Add your tee box devices</li>
              <li>• Invite team members</li>
              <li>• Set up billing</li>
              <li>• Launch your first campaign</li>
            </ul>
          </div>
        </div>
      )
    },
    {
      id: 1,
      title: 'Add Your Devices',
      description: 'Register your tee box displays to start managing content',
      icon: Monitor,
      content: (
        <div className="space-y-4">
          <p className="text-gray-600">
            Add your tee box display devices to the system. Each device will have a unique ID that you can find on the device label.
          </p>
          <div className="bg-green-50 p-4 rounded-lg">
            <h4 className="font-medium text-green-900 mb-2">Device Setup Tips:</h4>
            <ul className="text-sm text-green-800 space-y-1">
              <li>• Device IDs are usually on a sticker on the back</li>
              <li>• Name devices by hole number (e.g., "Tee Box 1")</li>
              <li>• Devices will appear online once they sync</li>
            </ul>
          </div>
        </div>
      )
    },
    {
      id: 2,
      title: 'Invite Team Members',
      description: 'Add staff members who will manage notices and content',
      icon: Users,
      content: (
        <div className="space-y-4">
          <p className="text-gray-600">
            Invite your course staff to help manage temporary notices and monitor device status.
          </p>
          <div className="bg-purple-50 p-4 rounded-lg">
            <h4 className="font-medium text-purple-900 mb-2">Team Member Permissions:</h4>
            <ul className="text-sm text-purple-800 space-y-1">
              <li>• Create temporary notices (max 1 hour)</li>
              <li>• View device status</li>
              <li>• Monitor active campaigns</li>
              <li>• Cannot modify sponsor content</li>
            </ul>
          </div>
        </div>
      )
    },
    {
      id: 3,
      title: 'Billing Setup',
      description: 'Complete your subscription setup',
      icon: CreditCard,
      content: (
        <div className="space-y-4">
          <p className="text-gray-600">
            Your 14-day free trial is active. Add a payment method to continue service after the trial period.
          </p>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <h4 className="font-medium text-yellow-900 mb-2">Billing Information:</h4>
            <ul className="text-sm text-yellow-800 space-y-1">
              <li>• 14-day free trial included</li>
              <li>• Cancel anytime</li>
              <li>• Secure payment processing via Stripe</li>
              <li>• Monthly or annual billing options</li>
            </ul>
          </div>
        </div>
      )
    }
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCompletedSteps(prev => [...prev, currentStep]);
      setCurrentStep(currentStep + 1);
    } else {
      setCompletedSteps(prev => [...prev, currentStep]);
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const isStepCompleted = (stepId: number) => completedSteps.includes(stepId);
  const currentStepData = steps[currentStep];
  const IconComponent = currentStepData.icon;

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Course Setup</h1>
          <p className="mt-2 text-gray-600">Get your golf course ready for digital displays</p>
        </div>

        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                  isStepCompleted(step.id) 
                    ? 'bg-green-500 border-green-500 text-white'
                    : currentStep === index
                    ? 'bg-blue-500 border-blue-500 text-white'
                    : 'bg-white border-gray-300 text-gray-400'
                }`}>
                  {isStepCompleted(step.id) ? (
                    <CheckCircle className="w-6 h-6" />
                  ) : (
                    <span className="text-sm font-medium">{index + 1}</span>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-16 h-1 mx-2 ${
                    isStepCompleted(step.id) ? 'bg-green-500' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <IconComponent className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <CardTitle>{currentStepData.title}</CardTitle>
                <CardDescription>{currentStepData.description}</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {currentStepData.content}
            
            <div className="flex justify-between mt-8">
              <Button
                variant="outline"
                onClick={handlePrevious}
                disabled={currentStep === 0}
              >
                Previous
              </Button>
              
              <div className="flex items-center space-x-2">
                <Badge variant="secondary">
                  Step {currentStep + 1} of {steps.length}
                </Badge>
                <Button onClick={handleNext}>
                  {currentStep === steps.length - 1 ? 'Complete Setup' : 'Next'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
