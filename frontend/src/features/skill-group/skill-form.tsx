import { SkillGroup } from "./ui/skill-group";
import { ALL_SKILLS, Skill, SkillLevel } from "./utils/types";
import { useState, useEffect } from 'react';
import { ChevronRight } from "lucide-react";
import "./skill-form.css"
import { ProfileParams } from "../../shared";
import { profileApi } from "../../shared/index";
import { useNavigate } from "react-router-dom";
import { ProfileParseResponse } from "../../shared/api/utils/types";




export const SkillForm: React.FC = () => {
    const [loading, setLoading] = useState(false);
    // const [parsedDescription, setParsedDescription] = useState<ProfileParseResponse | null>(null);
    const navigate = useNavigate();

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

    const parseSkills = async () => {
            const res = await profileApi.parseSkills(profile.customDescription)
            return res
        }

    const converter = (parsedDescription: ProfileParseResponse): ProfileParams => {
        const skillsMap: Record<string, string> = {}

        profile.skills.forEach((skill) => {
          skillsMap[skill.name] = skill.level
        })

        return {
            skills: {...parsedDescription?.data.skills, ...skillsMap},
            learning_goals: parsedDescription?.data.learning_goals || [],
            time_per_week: "medium"
        }
    }
    const handleRefresh = (parsedDescription: ProfileParseResponse) => {
        const data = converter(parsedDescription)
        console.log("Saving profile:", data);
        profileApi.updateProfile(data);
    };

    const handleSubmit = async () => {
        setLoading(true)
        try {
            if (!loading){
                const parsed: ProfileParseResponse = await parseSkills()
                await handleRefresh(parsed)
                navigate("/home")
            }
        } catch (error) {
            console.error("Error occurred while saving profile:", error);
        }
        setLoading(false)
    }

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
                    onClick={handleSubmit}
                    disabled={isInvalid || loading}
                >
                    Начать <ChevronRight size={20} />
                </button>
            </footer>
    </div>
    );
}