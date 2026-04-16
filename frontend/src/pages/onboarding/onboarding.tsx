import { SkillForm } from '../../features';
import { ThemeButton } from '../../shared';
import "./onboarding.css";

const Onboarding = () => {
  return (
    <div className="onboarding-page">
    <div className="onboarding-container">
        <div className="theme-block">
          <ThemeButton/>
        </div>
        <h1 className="brand-title">EEMA</h1>
        <p className="page-subtitle">Что умеешь?</p> 
        <div className="legend">
          <p className="legend-text">Выбери технологии и укажи свой уровень</p>
          <div className="legend-items">
            <span className="legend-item"><span className="legend-dot dot-low"/> Низкий</span>
            <span className="legend-item"><span className="legend-dot dot-mid"/> Средний</span>
            <span className="legend-item"><span className="legend-dot dot-high"/> Высокий</span>
          </div>
        </div>
        <SkillForm />    
      </div>
    </div>
  );
}

export default Onboarding;
