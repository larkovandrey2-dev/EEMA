import { Skill, SkillLevel } from "../utils/types";
import { SkillButton } from "./skill-button";
import "./skill-group.css"

interface SkillGroupProps {
    allSkills: string[];
    skills: Skill[];
    HandleRemove: (name: string) => void;
    HandleUpdate: (name: string, level: SkillLevel) => void;
    HandleAdd: (name: string, level: SkillLevel) => void;
}

export const SkillGroup: React.FC<SkillGroupProps> = ({allSkills, skills, HandleRemove, HandleUpdate, HandleAdd}) => {
    return (
    <div className="skills-grid">
        {allSkills.map((skillName) => {
            const currentSkill = skills.find(s => s.name === skillName);
            const isSelected = !!currentSkill;

            if (isSelected) {
                return (
                    <SkillButton 
                        key={`selected-${skillName}`}
                        skill={currentSkill} 
                        onRemove={() => HandleRemove(skillName)} 
                        onUpdate={(level) => HandleUpdate(skillName, level)} 
                    />
                );
            }

            return (
                <button 
                    key={`unselected-${skillName}`}
                    className="skill-add-btn" 
                    onClick={() => HandleAdd(skillName, "Beginner")}
                >
                    {skillName}
                </button>
            );
        })}
    </div>
    );
}