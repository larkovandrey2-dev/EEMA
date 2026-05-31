import "./like.css";
import { Heart } from "lucide-react";

export type likeButtonProps = {
    is_liked: boolean;
    onClick: () => void;
    isLoading: boolean;
}

export const LikeButton: React.FC<likeButtonProps> = ({ is_liked, onClick, isLoading }) => {

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
        e.preventDefault();
        if (!isLoading) {
            onClick();
        }
    }

    return (
        <button
            className={`courseUnit__like ${is_liked ? "liked" : ""}`}
            onClick={handleClick}
            disabled={isLoading}
            >
            <Heart/>
        </button>
    );
}