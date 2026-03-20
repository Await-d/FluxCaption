import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { AIProviderConfig } from '../api/aiProviders';

interface ProviderConfigDialogProps {
  provider: AIProviderConfig;
  onClose: () => void;
  onSave: (config: Partial<AIProviderConfig>) => void;
  isSaving?: boolean;
}

const ProviderConfigDialog: React.FC<ProviderConfigDialogProps> = ({
  provider,
  onClose,
  onSave,
  isSaving = false,
}) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    base_url: provider.base_url || '',
    timeout: provider.timeout || 30,
    default_model: provider.default_model || '',
    priority: provider.priority || 0,
  });

  useEffect(() => {
    setFormData({
      base_url: provider.base_url || '',
      timeout: provider.timeout || 30,
      default_model: provider.default_model || '',
      priority: provider.priority || 0,
    });
  }, [provider]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      is_enabled: provider.is_enabled,
      ...formData,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('ai_providers.configure_provider', 'Configure Provider')}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {provider.display_name} ({provider.provider_name})
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Base URL */}
          <div>
            <label htmlFor="provider-base-url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.base_url', 'Base URL')}
            </label>
            <input
              id="provider-base-url"
              type="text"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={t('ai_providers.base_url_placeholder', 'https://api.example.com')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('ai_providers.base_url_hint', 'API endpoint URL for this provider')}
            </p>
          </div>

          {/* Timeout */}
          <div>
            <label htmlFor="provider-timeout" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.timeout', 'Timeout (seconds)')}
            </label>
            <input
              id="provider-timeout"
              type="number"
              value={formData.timeout}
              onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 30 })}
              min="1"
              max="300"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('ai_providers.timeout_hint', 'Maximum wait time for API requests (1-300 seconds)')}
            </p>
          </div>

          {/* Default Model */}
          <div>
            <label htmlFor="provider-default-model" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.default_model', 'Default Model')}
            </label>
            <input
              id="provider-default-model"
              type="text"
              value={formData.default_model}
              onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
              placeholder={t('ai_providers.default_model_placeholder', 'gpt-4, claude-3-opus-20240229, etc.')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('ai_providers.default_model_hint', 'Default model to use for this provider')}
            </p>
          </div>

          {/* Priority */}
          <div>
            <label htmlFor="provider-priority" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.priority', 'Priority')}
            </label>
            <input
              id="provider-priority"
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              min="0"
              max="100"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('ai_providers.priority_hint', 'Higher priority providers are preferred (0-100)')}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              {t('common.cancel', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {t('common.saving', 'Saving...')}
                </>
              ) : (
                t('common.save', 'Save')
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProviderConfigDialog;
