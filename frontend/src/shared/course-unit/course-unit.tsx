import React from "react"
import "./course-unit.css"
import { LikeButton } from "../like-button/like";
import { profileApi } from "../api/users";


type CourseUnitProps = {
  id: number;
  title: string;
  url: string;
  stepik_id: number;

  difficulty: "easy" | "normal" | "hard" | null;
  is_paid: boolean;
  is_liked: boolean;
  price: number | null;

  learners_count: number;
  rating: number
  score?: number;
  reason: string;

  summary: string
  tags: string[]

  updated_at: string
}
export const CourseUnit: React.FC<CourseUnitProps> = ({id, title, url, difficulty, is_paid, price, learners_count, stepik_id, rating, score, reason, summary, updated_at, tags, is_liked}) => {
      const cur_difficulty = difficulty ? difficulty.toLocaleLowerCase() : "unknown"
      const [loading, setLoading] = React.useState(false);
      const [likedCur, setLikedCur] = React.useState(is_liked);

      const handleLikeClick = async () => {
        if (loading) return;
        setLoading(true);
        try {
          if (likedCur) {
            await profileApi.unlikeCourse(id);
          } else {
            await profileApi.likeCourse(id);
          }
          setLikedCur(prev => !prev);
        }
        catch {
          console.error("Ошибка при обновлении статуса лайка");
        }
        finally {
          setLoading(false);
        }
      }
      return (
        <a href={url} className="courseUnit">
            <div className="courseUnit__top">
                <h3 className="courseUnit__title">{title}</h3>

                <div className="courseUnit__meta">
                  <LikeButton is_liked={likedCur} onClick={handleLikeClick} isLoading={loading} />
                </div>
            </div>
            <div className="courseUnit__reason">
              {reason}
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