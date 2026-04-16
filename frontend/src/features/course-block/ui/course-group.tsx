import './course-group.css';
import { Course } from '../../../shared';
import { CourseUnit } from './course-unit';

interface CourseGroupProps {
  courses: Course[];
}

export const CourseGroup: React.FC<CourseGroupProps> = ({ courses }) => {
  return (
    <div className="course-grid">
      {courses.map((course) => (
        <CourseUnit key={course.id} id={course.id} difficulty={course.difficulty} title={course.title} url={course.url} is_paid={course.is_paid} price={course.price} learners_count={course.learners_count} />
      ))}
    </div>
  );
};
