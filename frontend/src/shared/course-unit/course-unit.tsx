import React from "react"
import { Course } from ".."
import "./course-unit.css"

export const CourseUnit: React.FC<Course> = ({id, title, url, difficulty, is_paid, price, learners_count, stepik_id, rating, similarity, summary, updated_at, tags}) => {
      const cur_difficulty = difficulty ? difficulty.toLocaleLowerCase() : "unknown"
      return (
        <a href={url} className="courseUnit">
            <div className="courseUnit__top">
                <h3 className="courseUnit__title">{title}</h3>

                <div className="courseUnit__meta">
                  <span className="courseUnit_match">{(similarity * 100).toFixed(1)}% match</span>
                </div>
            </div>

            <div className="courseUnit__meta">
                <span className="courseUnit_elem">👥 {learners_count} learners</span>

                <span className={`courseUnit__badge ${cur_difficulty}`}>
                  {cur_difficulty}
                </span>

                <span className="courseUnit_elem">
                    {is_paid ? (
                      <b>💰 {price}</b>
                    ) : (
                      <b className="free">FREE</b>
                    )}
                </span>
                {/*
                <span className="courseUnit_elem">rating: {rating.toFixed(1)}</span>
                */}
            </div>
        </a>
      );
    }