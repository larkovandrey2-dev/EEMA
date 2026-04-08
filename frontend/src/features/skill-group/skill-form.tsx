import { SkillGroup } from "./ui/skill-group";
import { ALL_SKILLS, Skill, SkillLevel } from "./utils/types";
import { useState, useEffect } from 'react';
import { ChevronRight } from "lucide-react";
import "./skill-form.css"





export const SkillForm: React.FC = () => {
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        //сделать
    })

    const [profile, setProfile] = useState({
        skills: [] as Skill[],
        customDescription: ""
    });

    const handleAdd = (name: string, level: SkillLevel) => {
        if (profile.skills.some(s => s.name === name)) return;
        setProfile(prev => ({
            ...prev,
            skills: [...prev.skills, { name, level }]
        }));
    };

    const handleRemove = (name: string) => {
        setProfile(prev => ({
            ...prev,
            skills: prev.skills.filter(s => s.name !== name)
        }));
    };

    const handleUpdate = (name: string, level: SkillLevel) => {
        setProfile(prev => ({
            ...prev,
            skills: prev.skills.map(s => s.name === name ? { ...s, level } : s)
        }));
    };

    const handleRefresh = () => {
        console.log("Saving profile:", profile);
        //сделать
    };

    const isInvalid = profile.skills.length === 0 && !profile.customDescription.trim();

    return (
    <div>
        <SkillGroup 
        allSkills={ALL_SKILLS} 
        skills={profile.skills} HandleAdd={handleAdd} 
        HandleRemove={handleRemove} 
        HandleUpdate={handleUpdate}/>
        <div className="description-section">
                <h2>Опиши навыки своими словами</h2>
                <textarea
                    className="skill-textarea"
                    placeholder="Например: Пишу на Python около года..."
                    value={profile.customDescription}
                    onChange={(e) => setProfile({ ...profile, customDescription: e.target.value })}
                />
            </div>

            <footer className="form-footer">
                <button 
                    className="submit-btn" 
                    onClick={handleRefresh}
                    disabled={isInvalid}
                >
                    Начать <ChevronRight size={20} />
                </button>
            </footer>
    </div>
    );
}