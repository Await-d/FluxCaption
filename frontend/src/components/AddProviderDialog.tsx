import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';

interface AddProviderDialogProps {
  onClose: () => void;
  onAdd: (config: {
    provider_name: string;
    display_name: string;
    base_url?: string;
    timeout?: number;
    default_model?: string;
    priority?: number;
    description?: string;
  }) => void;
  isAdding?: boolean;
}

const AddProviderDialog: React.FC<AddProviderDialogProps> = ({ onClose, onAdd, isAdding = false }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    provider_name: '',
    display_name: '',
    base_url: '',
    timeout: 30,
    default_model: '',
    priority: 0,
    description: '',
  });

  // 预定义的提供商列表
  const predefinedProviders = [
    {
      provider_name: 'openai',
      display_name: t('ai_providers.predefined.openai.name', 'OpenAI (GPT)'),
      description: t('ai_providers.predefined.openai.desc', 'OpenAI GPT models (GPT-4, GPT-3.5, etc.)'),
      base_url: 'https://api.openai.com/v1',
    },
    {
      provider_name: 'claude',
      display_name: t('ai_providers.predefined.claude.name', 'Claude (Anthropic)'),
      description: t('ai_providers.predefined.claude.desc', 'Anthropic Claude models (Opus, Sonnet, Haiku)'),
      base_url: 'https://api.anthropic.com/v1',
    },
    {
      provider_name: 'deepseek',
      display_name: t('ai_providers.predefined.deepseek.name', 'DeepSeek'),
      description: t('ai_providers.predefined.deepseek.desc', 'DeepSeek AI models (affordable and powerful)'),
      base_url: 'https://api.deepseek.com/v1',
    },
    {
      provider_name: 'gemini',
      display_name: t('ai_providers.predefined.gemini.name', 'Gemini (Google)'),
      description: t('ai_providers.predefined.gemini.desc', 'Google Gemini models'),
      base_url: 'https://generativelanguage.googleapis.com/v1',
    },
    {
      provider_name: 'zhipu',
      display_name: t('ai_providers.predefined.zhipu.name', '智谱AI (GLM)'),
      description: t('ai_providers.predefined.zhipu.desc', '智谱AI GLM models - Chinese-optimized'),
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
    },
    {
      provider_name: 'moonshot',
      display_name: t('ai_providers.predefined.moonshot.name', 'Moonshot AI (Kimi)'),
      description: t('ai_providers.predefined.moonshot.desc', 'Moonshot Kimi models - Super long context'),
      base_url: 'https://api.moonshot.cn/v1',
    },
    {
      provider_name: 'custom_openai',
      display_name: t('ai_providers.predefined.custom_openai.name', 'Custom OpenAI Compatible'),
      description: t('ai_providers.predefined.custom_openai.desc', 'Custom OpenAI-compatible endpoint (OpenRouter, LocalAI, vLLM, etc.)'),
      base_url: '',
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.provider_name || !formData.display_name) {
      alert(t('ai_providers.provider_name_required', 'Provider name and display name are required'));
      return;
    }
    onAdd(formData);
  };

  const handleSelectPredefined = (provider: typeof predefinedProviders[0]) => {
    setFormData({
      ...formData,
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      description: provider.description,
      base_url: provider.base_url,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('ai_providers.add_provider', 'Add Provider')}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {t('ai_providers.add_provider_hint', 'Add a new AI provider or restore a deleted one')}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Predefined Providers */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            {t('ai_providers.quick_add', 'Quick Add')}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {predefinedProviders.map((provider) => (
              <button
                key={provider.provider_name}
                onClick={() => handleSelectPredefined(provider)}
                className={`p-3 border-2 rounded-lg text-left transition-colors ${
                  formData.provider_name === provider.provider_name
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                }`}
              >
                <p className="font-medium text-gray-900 dark:text-white">{provider.display_name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                  {provider.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Provider Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('ai_providers.provider_name', 'Provider Name')} *
              </label>
              <input
                type="text"
                value={formData.provider_name}
                onChange={(e) => setFormData({ ...formData, provider_name: e.target.value })}
                placeholder={t('ai_providers.provider_name_placeholder', 'openai, claude, custom_provider')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                required
              />
            </div>

            {/* Display Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('ai_providers.display_name', 'Display Name')} *
              </label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder={t('ai_providers.display_name_placeholder', 'OpenAI (GPT)')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                required
              />
            </div>
          </div>

          {/* Base URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.base_url', 'Base URL')}
            </label>
            <input
              type="text"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={t('ai_providers.base_url_placeholder', 'https://api.example.com/v1')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            {/* Timeout */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('ai_providers.timeout', 'Timeout (seconds)')}
              </label>
              <input
                type="number"
                value={formData.timeout}
                onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 30 })}
                min="1"
                max="300"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('ai_providers.priority', 'Priority')}
              </label>
              <input
                type="number"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                min="0"
                max="100"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Default Model */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('ai_providers.default_model', 'Default Model')}
              </label>
              <input
                type="text"
                value={formData.default_model}
                onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
                placeholder={t('ai_providers.default_model_placeholder', 'gpt-4, claude-3')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ai_providers.description', 'Description')}
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder={t('ai_providers.description_placeholder', 'Provider description...')}
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isAdding}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              {t('common.cancel', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={isAdding}
              className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              {isAdding ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {t('ai_providers.adding', 'Adding...')}
                </>
              ) : (
                t('ai_providers.add_provider', 'Add Provider')
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddProviderDialog;
