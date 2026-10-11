import React from 'react';
import { ArrowUpRight, Maximize2, Building2, FileCheck2, Car } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function ExamplePrompts({ language, onSelectExample, isLoading }) {
  const t = translations[language];

  const categories = [
    {
      id: 'setbacks',
      title: t.catSetbacks,
      icon: <Maximize2 size={18} className="cat-icon" />,
      questions: [
        t.exampleSetback1,
        t.exampleSetback2
      ]
    },
    {
      id: 'far',
      title: t.catFAR,
      icon: <Building2 size={18} className="cat-icon" />,
      questions: [
        t.exampleFAR1,
        t.exampleFAR2
      ]
    },
    {
      id: 'permissions',
      title: t.catPermissions,
      icon: <FileCheck2 size={18} className="cat-icon" />,
      questions: [
        t.examplePermission1
      ]
    },
    {
      id: 'parking',
      title: t.catSafety,
      icon: <Car size={18} className="cat-icon" />,
      questions: [
        t.exampleParking1
      ]
    }
  ];

  return (
    <section className="example-prompts-section">
      <div className="container">
        <div className="section-header">
          <h3 className="section-title">{t.examplesTitle}</h3>
          <p className="section-subtitle">{t.examplesSubtitle}</p>
        </div>

        <div className="example-cards-grid">
          {categories.map((cat) => (
            <div key={cat.id} className="category-group">
              <div className="category-header">
                {cat.icon}
                <span className="category-title">{cat.title}</span>
              </div>
              <div className="questions-list">
                {cat.questions.map((q, idx) => (
                  <button
                    key={idx}
                    type="button"
                    disabled={isLoading}
                    className="example-prompt-card civic-card"
                    onClick={() => onSelectExample(q)}
                  >
                    <span className="prompt-text">{q}</span>
                    <span className="prompt-action-icon">
                      <ArrowUpRight size={16} />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
