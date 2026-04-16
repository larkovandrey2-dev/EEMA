import React from 'react';
import { Skill, SkillLevel } from '../utils/types';
import {X} from "lucide-react";
import { SKILL_LEVELS } from '../utils/types';
import "./skill-button.css"

interface SkillButtonProps {
    skill: Skill;
    onRemove: () => void;
    onUpdate: (level: SkillLevel) => void;
}

export const SkillButton: React.FC<SkillButtonProps> = ({ skill, onRemove, onUpdate }) => {
    return (
    <div className={`skill-badge level-${skill.level.toLowerCase()}`}>
        <span className="skill-name">{skill.name}</span>
        <div className="skill-controls">
            <div className="level-dots">
                {SKILL_LEVELS.map(level => (
                    <button 
                        key={level} 
                        onClick={() => onUpdate(level)} 
                        className={`dot-btn dot-${level.toLowerCase()}`}
                        data-active={skill.level === level}
                        title={level}
                    />
                ))}
            </div>
            <div className="separator"/>
            <button className="remove-btn" onClick={onRemove}>
                <X size={14}/>
            </button>
        </div>
    </div>
    );
}