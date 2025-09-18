"use client";

import { useEffect, useState } from 'react';
import ImagePasteField from '@/components/ImagePasteField';

interface Template {
  id: string;
  title: string;
  content: string;
  author: string | null;
  linkedin_url: string | null;
  category: string;
  format: string;
  tags: string[];
  screenshot_url: string | null;
  created_at: string;
}

const CATEGORIES = [
  { value: 'attract', label: 'Attract', description: 'Build awareness and trust' },
  { value: 'nurture', label: 'Nurture', description: 'Show authority/create demand' },
  { value: 'convert', label: 'Convert', description: 'Qualify and filter buyers' }
];

const FORMATS = {
  attract: [
    { value: 'belief_shift', label: 'Belief Shift' },
    { value: 'origin_story', label: 'Origin Story' },
    { value: 'industry_myths', label: 'Industry Myths' }
  ],
  nurture: [
    { value: 'framework', label: 'Framework' },
    { value: 'step_by_step', label: 'Step-by-step' },
    { value: 'how_i_how_to', label: 'How I / How to' }
  ],
  convert: [
    { value: 'objection_post', label: 'Objection Post' },
    { value: 'result_breakdown', label: 'Result Breakdown' },
    { value: 'client_success_story', label: 'Client Success Story' }
  ]
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: 'attract',
    format: 'belief_shift',
    author: '',
    linkedin_url: '',
    tags: '',
    screenshot_url: ''
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch('http://localhost:8000/templates');
      if (!response.ok) throw new Error('Failed to fetch templates');
      const data = await response.json();
      setTemplates(data.templates);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        tags: formData.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
      };

      const response = await fetch('http://localhost:8000/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to create template');
      
      await fetchTemplates();
      resetForm();
      setShowForm(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      const response = await fetch(`http://localhost:8000/templates/${templateId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete template');
      
      await fetchTemplates();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      content: '',
      category: 'attract',
      format: 'belief_shift',
      author: '',
      linkedin_url: '',
      tags: '',
      screenshot_url: ''
    });
    setEditingTemplate(null);
  };

  const startEdit = (template: Template) => {
    setFormData({
      title: template.title,
      content: template.content,
      category: template.category,
      format: template.format,
      author: template.author || '',
      linkedin_url: template.linkedin_url || '',
      tags: template.tags.join(', '),
      screenshot_url: template.screenshot_url || ''
    });
    setEditingTemplate(template);
    setShowForm(true);
  };

  if (loading && templates.length === 0) {
    return <div className="container mx-auto p-4 text-center">Loading templates...</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Content Templates</h1>
        <button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          Add Template
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
          {error}
        </div>
      )}

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
          <h2 className="text-2xl font-semibold mb-4">
            {editingTemplate ? 'Edit Template' : 'Add New Template'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Author</label>
                <input
                  type="text"
                  value={formData.author}
                  onChange={(e) => setFormData({...formData, author: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value, format: FORMATS[e.target.value as keyof typeof FORMATS][0].value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label} - {cat.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Format</label>
                <select
                  value={formData.format}
                  onChange={(e) => setFormData({...formData, format: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {FORMATS[formData.category as keyof typeof FORMATS].map(format => (
                    <option key={format.value} value={format.value}>
                      {format.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({...formData, content: e.target.value})}
                rows={8}
                className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans text-[15px] leading-[22px] resize-none"
                placeholder="Write your LinkedIn post content here... Use line breaks for paragraphs and proper formatting."
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">LinkedIn URL</label>
                <input
                  type="url"
                  value={formData.linkedin_url}
                  onChange={(e) => setFormData({...formData, linkedin_url: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({...formData, tags: e.target.value})}
                  placeholder="hook, social_proof, cta"
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Screenshot (optional)</label>
              <ImagePasteField
                value={formData.screenshot_url}
                onChange={(url) => setFormData({...formData, screenshot_url: url})}
                placeholder="Paste screenshot here (Cmd+V) or enter URL manually"
              />
            </div>

            <div className="flex gap-4">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : (editingTemplate ? 'Update Template' : 'Create Template')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
                className="bg-gray-500 text-white px-6 py-2 rounded-md hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white shadow-md rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Templates ({templates.length})</h2>
        </div>
        
        {templates.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No templates yet. Add your first template to get started!
          </div>
        ) : (
          <div className="space-y-4">
            {templates.map((template) => (
              <div key={template.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-3">
                      <h3 className="text-lg font-semibold text-gray-900 leading-tight">{template.title}</h3>
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        template.category === 'attract' ? 'bg-blue-100 text-blue-800' :
                        template.category === 'nurture' ? 'bg-green-100 text-green-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {template.category}
                      </span>
                      <span className="px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-800">
                        {template.format.replace('_', ' ')}
                      </span>
                    </div>
                    
                    {template.author && (
                      <p className="text-sm text-gray-500 mb-3 font-medium">By {template.author}</p>
                    )}
                    
                    <div className="text-gray-700 mb-4 max-h-40 overflow-y-auto font-sans text-[15px] leading-[22px] whitespace-pre-wrap bg-gray-50 p-3 rounded-md border border-gray-100">
                      {template.content}
                    </div>
                    
                    {template.tags.length > 0 && (
                      <div className="flex gap-1 mb-2">
                        {template.tags.map((tag, index) => (
                          <span key={index} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    <p className="text-xs text-gray-500">
                      Created: {new Date(template.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => startEdit(template)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(template.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
