import React, { useState } from 'react';
import { Save, Database, Cloud, Github, Settings as SettingsIcon, Server, BarChart3, Zap, CheckCircle, AlertCircle, MessageSquare } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '../services/api';

interface ServiceConfig {
  id: string;
  name: string;
  category: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  color: string;
  configured: boolean;
  fields: ConfigField[];
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number';
  placeholder: string;
  required: boolean;
  description?: string;
}

export const SettingsPage: React.FC = () => {
  const [selectedService, setSelectedService] = useState<ServiceConfig | null>(null);
  const [configs, setConfigs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const services: ServiceConfig[] = [
    // Application Life Cycle
    {
      id: 'jira',
      name: 'Jira',
      category: 'Application Life Cycle',
      icon: SettingsIcon,
      color: 'bg-blue-600',
      configured: false,
      fields: [
        { key: 'JIRA_SERVER', label: 'Jira Server URL', type: 'url', placeholder: 'https://your-company.atlassian.net', required: true },
        { key: 'JIRA_EMAIL', label: 'Email', type: 'text', placeholder: 'user@company.com', required: true },
        { key: 'JIRA_TOKEN', label: 'API Token', type: 'password', placeholder: 'Your Jira API token', required: true },
        { key: 'PROJECT_KEY', label: 'Project Key', type: 'text', placeholder: 'IPM', required: true }
      ]
    },
    {
      id: 'gitlab',
      name: 'GitLab',
      category: 'Application Life Cycle',
      icon: SettingsIcon,
      color: 'bg-orange-600',
      configured: false,
      fields: [
        { key: 'GITLAB_URL', label: 'GitLab URL', type: 'url', placeholder: 'https://gitlab.com', required: true },
        { key: 'GITLAB_TOKEN', label: 'Access Token', type: 'password', placeholder: 'glpat-xxxxxxxxxxxx', required: true },
        { key: 'GITLAB_PROJECT_ID', label: 'Project ID', type: 'text', placeholder: '12345', required: true }
      ]
    },
    {
      id: 'github',
      name: 'GitHub',
      category: 'Application Life Cycle',
      icon: Github,
      color: 'bg-gray-800',
      configured: true,
      fields: [
        { key: 'GITHUB_TOKEN', label: 'Personal Access Token', type: 'password', placeholder: 'ghp_xxxxxxxxxxxx', required: true },
        { key: 'GITHUB_REPO_OWNER', label: 'Repository Owner', type: 'text', placeholder: 'your-organization', required: true },
        { key: 'GITHUB_REPO_NAME', label: 'Repository Name', type: 'text', placeholder: 'your-repo', required: true }
      ]
    },

    // Data Stores and Cache
    {
      id: 'postgresql',
      name: 'PostgreSQL',
      category: 'Data Stores and Cache',
      icon: Database,
      color: 'bg-blue-700',
      configured: false,
      fields: [
        { key: 'POSTGRES_HOST', label: 'Host', type: 'text', placeholder: 'localhost', required: true },
        { key: 'POSTGRES_PORT', label: 'Port', type: 'number', placeholder: '5432', required: true },
        { key: 'POSTGRES_DATABASE', label: 'Database', type: 'text', placeholder: 'aristotlei', required: true },
        { key: 'POSTGRES_USERNAME', label: 'Username', type: 'text', placeholder: 'postgres', required: true },
        { key: 'POSTGRES_PASSWORD', label: 'Password', type: 'password', placeholder: 'your-password', required: true }
      ]
    },
    {
      id: 'redis',
      name: 'Redis',
      category: 'Data Stores and Cache',
      icon: Database,
      color: 'bg-red-600',
      configured: false,
      fields: [
        { key: 'REDIS_HOST', label: 'Host', type: 'text', placeholder: 'localhost', required: true },
        { key: 'REDIS_PORT', label: 'Port', type: 'number', placeholder: '6379', required: true },
        { key: 'REDIS_PASSWORD', label: 'Password', type: 'password', placeholder: 'your-password', required: false }
      ]
    },

    // Queue
    {
      id: 'rabbitmq',
      name: 'RabbitMQ',
      category: 'Queue',
      icon: MessageSquare,
      color: 'bg-orange-500',
      configured: false,
      fields: [
        { key: 'RABBITMQ_HOST', label: 'Host', type: 'text', placeholder: 'localhost', required: true },
        { key: 'RABBITMQ_PORT', label: 'Port', type: 'number', placeholder: '5672', required: true },
        { key: 'RABBITMQ_USERNAME', label: 'Username', type: 'text', placeholder: 'guest', required: true },
        { key: 'RABBITMQ_PASSWORD', label: 'Password', type: 'password', placeholder: 'guest', required: true },
        { key: 'RABBITMQ_VHOST', label: 'Virtual Host', type: 'text', placeholder: '/', required: false }
      ]
    },

    // LLMs
    {
      id: 'openrouter',
      name: 'OpenRouter AI',
      category: 'LLMs',
      icon: Zap,
      color: 'bg-purple-600',
      configured: false,
      fields: [
        { key: 'OPENROUTER_API_KEY', label: 'API Key', type: 'password', placeholder: 'sk-or-v1-xxxxxxxxxxxx', required: true },
        { key: 'OPENROUTER_MODEL', label: 'Default Model', type: 'text', placeholder: 'anthropic/claude-3-sonnet', required: true },
        { key: 'OPENROUTER_MAX_TOKENS', label: 'Max Tokens', type: 'number', placeholder: '4000', required: false }
      ]
    },

    // Analytics
    {
      id: 'mongodb-atlas-charts',
      name: 'MongoDB Atlas',
      category: 'Analytics',
      icon: BarChart3,
      color: 'bg-green-600',
      configured: false,
      fields: [
        { key: 'MONGODB_ATLAS_CHARTS_URL', label: 'Charts URL', type: 'url', placeholder: 'https://charts.mongodb.com/charts-project-xxxxx', required: true },
        { key: 'MONGODB_ATLAS_API_KEY', label: 'API Key', type: 'password', placeholder: 'your-api-key', required: true },
        { key: 'MONGODB_ATLAS_PROJECT_ID', label: 'Project ID', type: 'text', placeholder: 'project-id', required: true }
      ]
    },
    {
      id: 'grafana',
      name: 'Grafana',
      category: 'Analytics',
      icon: BarChart3,
      color: 'bg-orange-600',
      configured: false,
      fields: [
        { key: 'GRAFANA_URL', label: 'Grafana URL', type: 'url', placeholder: 'https://your-grafana.com', required: true },
        { key: 'GRAFANA_API_KEY', label: 'API Key', type: 'password', placeholder: 'your-grafana-api-key', required: true },
        { key: 'GRAFANA_ORG_ID', label: 'Organization ID', type: 'text', placeholder: '1', required: false },
        { key: 'GRAFANA_DASHBOARD_ID', label: 'Dashboard ID', type: 'text', placeholder: 'dashboard-id', required: false }
      ]
    },

    // Cloud
    {
      id: 'aws',
      name: 'AWS',
      category: 'Cloud',
      icon: Cloud,
      color: 'bg-orange-500',
      configured: false,
      fields: [
        { key: 'AWS_ACCESS_KEY_ID', label: 'Access Key ID', type: 'password', placeholder: 'AKIAIOSFODNN7EXAMPLE', required: true },
        { key: 'AWS_SECRET_ACCESS_KEY', label: 'Secret Access Key', type: 'password', placeholder: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', required: true },
        { key: 'AWS_REGION', label: 'Region', type: 'text', placeholder: 'us-east-1', required: true },
        { key: 'AWS_S3_BUCKET', label: 'S3 Bucket', type: 'text', placeholder: 'your-bucket-name', required: false }
      ]
    },
    {
      id: 'gcp',
      name: 'Google Cloud',
      category: 'Cloud',
      icon: Cloud,
      color: 'bg-red-500',
      configured: false,
      fields: [
        { key: 'GCP_PROJECT_ID', label: 'Project ID', type: 'text', placeholder: 'your-project-id', required: true },
        { key: 'GCP_SERVICE_ACCOUNT_KEY', label: 'Service Account Key (JSON)', type: 'password', placeholder: 'Paste your service account JSON here', required: true },
        { key: 'GCP_REGION', label: 'Region', type: 'text', placeholder: 'us-central1', required: true }
      ]
    },

    // Deployment
    {
      id: 'docker',
      name: 'Docker',
      category: 'Deployment',
      icon: Server,
      color: 'bg-blue-500',
      configured: false,
      fields: [
        { key: 'DOCKER_REGISTRY', label: 'Registry URL', type: 'url', placeholder: 'https://registry.hub.docker.com', required: false },
        { key: 'DOCKER_USERNAME', label: 'Username', type: 'text', placeholder: 'your-username', required: false },
        { key: 'DOCKER_PASSWORD', label: 'Password/Token', type: 'password', placeholder: 'your-password', required: false }
      ]
    }
  ];

  const categories = [
    'Application Life Cycle',
    'Data Stores and Cache',
    'Queue',
    'LLMs',
    'Analytics',
    'Cloud',
    'Deployment'
  ];

  const handleInputChange = (key: string, value: string) => {
    setConfigs(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveSettings = async () => {
    if (!selectedService) return;

    setSaving(true);
    setSaveStatus('idle');

    try {
      await api.saveConfig(selectedService.id, configs);
      selectedService.configured = true;
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('Failed to save configuration:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } finally {
      setSaving(false);
    }
  };

  const getSaveButtonContent = () => {
    if (saving) return 'Saving...';
    if (saveStatus === 'success') return 'Saved Successfully!';
    if (saveStatus === 'error') return 'Save Failed';
    return 'Save Configuration';
  };

  const getSaveButtonIcon = () => {
    if (saving) return <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />;
    if (saveStatus === 'success') return <CheckCircle className="w-5 h-5" />;
    if (saveStatus === 'error') return <AlertCircle className="w-5 h-5" />;
    return <Save className="w-5 h-5" />;
  };

  const getSaveButtonColor = () => {
    if (saveStatus === 'success') return 'bg-green-600 hover:bg-green-700';
    if (saveStatus === 'error') return 'bg-red-600 hover:bg-red-700';
    return 'bg-blue-600 hover:bg-blue-700';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Configuration Settings</h1>
        <p className="text-slate-600">Configure your integrations and services</p>
      </div>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-200px)]">
        {/* Left Panel - Service Categories */}
        <div className="col-span-6 bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-6 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900">Services</h2>
          </div>

          <div className="p-6 space-y-8 overflow-y-auto max-h-[calc(100vh-320px)]">
            {categories.map((category, categoryIndex) => (
              <motion.div
                key={category}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: categoryIndex * 0.1 }}
                className="relative"
              >
                {/* Category Header with Gradient Line */}
                <div className="relative mb-6">
                  <h3 className="text-sm font-semibold text-slate-800 mb-4 uppercase tracking-wider">
                    {categoryIndex + 1}. {category}
                  </h3>
                  <div className="absolute -bottom-2 left-0 right-0 h-px bg-gradient-to-r from-slate-300 via-slate-200 to-transparent"></div>
                </div>

                {/* Services Grid */}
                <div className="grid grid-cols-3 gap-4 mb-8">
                  {services
                    .filter(service => service.category === category)
                    .map((service, serviceIndex) => {
                      const Icon = service.icon;
                      return (
                        <motion.button
                          key={service.id}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ duration: 0.2, delay: serviceIndex * 0.05 }}
                          whileHover={{
                            scale: 1.05,
                            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
                          }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => setSelectedService(service)}
                          className={`group relative flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all duration-300 ${
                            selectedService?.id === service.id
                              ? 'border-blue-500 bg-blue-50 shadow-lg'
                              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 shadow-sm'
                          }`}
                        >
                          {/* Service Icon */}
                          <div className={`relative p-3 rounded-lg ${service.color} group-hover:scale-110 transition-transform duration-300`}>
                            <Icon className="w-6 h-6 text-white" />
                          </div>

                          {/* Service Name */}
                          <div className="text-center">
                            <div className="font-medium text-slate-900 text-sm leading-tight">
                              {service.name}
                            </div>
                          </div>

                          {/* Status Indicator */}
                          <div className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-white shadow-sm ${
                            service.configured ? 'bg-green-500' : 'bg-red-500'
                          }`} />

                          {/* Hover Effect Overlay */}
                          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        </motion.button>
                      );
                    })}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right Panel - Configuration Form */}
        <div className="col-span-6 bg-white rounded-xl shadow-sm border border-slate-200">
          {selectedService ? (
            <div className="h-full flex flex-col">
              {/* Header */}
              <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`p-4 rounded-xl ${selectedService.color} shadow-lg`}>
                      <selectedService.icon className="w-8 h-8 text-white" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-slate-900">{selectedService.name}</h2>
                      <p className="text-slate-600 font-medium">{selectedService.category}</p>
                    </div>
                  </div>
                  <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold shadow-sm ${
                    selectedService.configured
                      ? 'bg-green-100 text-green-800 border border-green-200'
                      : 'bg-red-100 text-red-800 border border-red-200'
                  }`}>
                    <div className={`w-3 h-3 rounded-full ${
                      selectedService.configured ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    {selectedService.configured ? 'Configured' : 'Not Configured'}
                  </div>
                </div>
              </div>

              {/* Form */}
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="space-y-6">
                  {selectedService.fields.map((field, index) => (
                    <motion.div
                      key={field.key}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                      className="group"
                    >
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        {field.label}
                        {field.required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      <input
                        type={field.type}
                        value={configs[field.key] || ''}
                        onChange={(e) => handleInputChange(field.key, e.target.value)}
                        className="w-full px-4 py-3 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300 group-hover:border-slate-300"
                        placeholder={field.placeholder}
                        required={field.required}
                      />
                      {field.description && (
                        <p className="text-xs text-slate-500 mt-2 italic">{field.description}</p>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Save Button */}
              <div className="p-6 border-t border-slate-200 bg-gradient-to-r from-slate-50 to-white">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSaveSettings}
                  disabled={saving}
                  className={`w-full flex items-center justify-center gap-3 px-6 py-4 rounded-lg font-semibold text-white transition-all duration-300 shadow-lg ${getSaveButtonColor()} disabled:opacity-50`}
                >
                  {getSaveButtonIcon()}
                  {getSaveButtonContent()}
                </motion.button>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-slate-50 to-white">
              <div className="text-center">
                <div className="w-20 h-20 bg-gradient-to-br from-slate-200 to-slate-300 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                  <SettingsIcon className="w-10 h-10 text-slate-500" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Select a Service</h3>
                <p className="text-slate-600 max-w-sm">Choose a service from the left panel to configure its settings and start integrating with your workflow</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};