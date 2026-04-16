import React from "react"
import { Course } from "../../../shared"
import "./course-unit.css"

export const CourseUnit: React.FC<Course> = ({id, title, url, difficulty, is_paid, price, learners_count}) => {
      const cur_difficulty = difficulty ? difficulty.toLocaleLowerCase() : "unknown"
      return (
        <a href={url} className="courseUnit">
            <div className="courseUnit__top">
                <h3 className="courseUnit__title">{title}</h3>
                {!!difficulty ?
                <span className={`courseUnit__badge ${cur_difficulty}`}>
                  {cur_difficulty}
                </span>: "unknown"
              }
            </div>

            <div className="courseUnit__meta">
                <span>👥 {learners_count} learners</span>
        
                <span>
                    {is_paid ? (
                      <b>💰 {price}</b>
                    ) : (
                      <b className="free">FREE</b>
                    )}
                </span>
            </div>
        </a>
      );
    }