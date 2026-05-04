import { Markov } from "../../../shared";
import "./markov.css";

type MarkovCourseProps = {
  markov: Markov;
  id: number;
};

const MarkovCourse: React.FC<MarkovCourseProps> = ({ markov, id }) => {
  const { title, url, difficulty, learners_count } = markov;

  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="markov-card"
    >
      <div className="markov-index">{id}</div>

      <div className="markov-body">
        <div className="markov-title">{title}</div>

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