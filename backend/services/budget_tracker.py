from backend.config import (
    IMAGE_COST_PER_UNIT, VIDEO_COST_FAST, VIDEO_COST_STD,
    TOTAL_BUDGET, IMAGE_BUDGET
)

class BudgetTracker:
    """Track image and video generation costs against $100 credit."""

    def __init__(self):
        self.images_generated = 0
        self.videos_generated = 0
        self.image_cost = 0.0
        self.video_cost = 0.0

    @property
    def total_cost(self) -> float:
        return self.image_cost + self.video_cost

    def can_generate_image(self) -> bool:
        return self.total_cost < (TOTAL_BUDGET * 0.8)

    def can_generate_video(self) -> bool:
        return self.total_cost + VIDEO_COST_FAST < (TOTAL_BUDGET * 0.8)

    def record_image(self, num_images: int = 1):
        self.images_generated += num_images
        self.image_cost = self.images_generated * IMAGE_COST_PER_UNIT

    def record_video(self, tier: str = "fast"):
        self.videos_generated += 1
        cost = VIDEO_COST_FAST if tier == "fast" else VIDEO_COST_STD
        self.video_cost += cost

    def get_status(self) -> dict:
        return {
            "images_generated": self.images_generated,
            "videos_generated": self.videos_generated,
            "image_cost": f"${self.image_cost:.2f}",
            "video_cost": f"${self.video_cost:.2f}",
            "total_cost": f"${self.total_cost:.2f}",
            "budget_remaining": f"${TOTAL_BUDGET - self.total_cost:.2f}",
        }

# Singleton
budget_tracker = BudgetTracker()
