import { Markov } from "../../../shared";
import "./markov.css";
import React from "react";
import { profileApi, LikeButton } from "../../../shared/index";


type MarkovCourseProps = {
  markov: Markov;
  id_num: number;
};

const MarkovCourse: React.FC<MarkovCourseProps> = ({ markov, id_num }) => {
  const { title, url, difficulty, learners_count, id, is_liked, markov_reason } = markov;

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
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="markov-card"
    >
      <div className="markov-index">{id_num}</div>

      <div className="markov-body">
        <div className="courseUnit__top">
          <div className="markov-title">
            {title}
          </div>
          <LikeButton is_liked={likedCur} onClick={handleLikeClick} isLoading={loading} />
          </div>
        <div className="courseUnit__reason">
          {markov_reason}
        </div>
        <div className="markov-meta">
          <span className="markov-difficulty">{difficulty}</span>
          <span className="markov-separator">•</span>
          <span className="markov-learners">
            {learners_count.toLocaleString()} обучающихся
          </span>
        </div>
      </div>
    </a>
  );
};

export default MarkovCourse;