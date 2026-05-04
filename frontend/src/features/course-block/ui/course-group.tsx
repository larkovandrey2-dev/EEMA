import './course-group.css';
import { Course } from '../../../shared';
import { CourseUnit } from '../../../shared/course-unit/course-unit';

export interface CourseGroupProps {
  courses: Course[];
}

export const CourseGroup: React.FC<CourseGroupProps> = ({ courses }) => {
  return (
    <div className="course-grid">
      {courses.map((course) => (
        <CourseUnit key={course.id} id={course.id} difficulty={course.difficulty} title={course.title} url={course.url} is_paid={course.is_paid} price={course.price} learners_count={course.learners_count} stepik_id={course.stepik_id} rating={course.rating} similarity={course.similarity} summary={course.summary} updated_at={course.updated_at} tags={course.tags} />
      ))}
    </div>
  );
};
