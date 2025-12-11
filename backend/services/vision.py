"""
Vision Service Module
Handles CNN inference and disease detection
"""

import os
import torch
import torch.nn.functional as F
from PIL import Image
from pathlib import Path
from torchvision import transforms
from efficientnet_pytorch import EfficientNet

class VisionService:
    """CNN-based plant disease detection service."""
    
    def __init__(self, checkpoint_path: str, device: str = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model, self.class_names = self._load_model(checkpoint_path)
        self.transform = self._get_transform()
    
    def _load_model(self, checkpoint_path: str):
        """Load EfficientNet-B0 model from checkpoint."""
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        class_names = checkpoint["classes"]
        
        model = EfficientNet.from_pretrained(
            "efficientnet-b0",
            num_classes=len(class_names)
        )
        model.load_state_dict(checkpoint["model"])
        model.to(self.device)
        model.eval()
        
        return model, class_names
    
    def _get_transform(self):
        """Return standard image transform."""
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
    
    def predict(self, image_path: str = None, image_pil: Image.Image = None) -> dict:
        """
        Predict disease from image.
        
        Args:
            image_path: Path to image file OR
            image_pil: PIL Image object
        
        Returns:
            {
                "disease": "Tomato Early Blight",
                "confidence": 0.92,
                "all_predictions": [{"class": "...", "confidence": 0.92}, ...]
            }
        """
        if image_path:
            img = Image.open(image_path).convert("RGB")
        elif image_pil:
            img = image_pil.convert("RGB")
        else:
            raise ValueError("Provide either image_path or image_pil")
        
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logits = self.model(img_tensor)
            probs = F.softmax(logits, dim=1)[0]
        
        conf, idx = torch.max(probs, 0)
        top_disease = self.class_names[idx.item()]
        top_confidence = float(conf)
        
        # Get top-5 predictions
        top5_conf, top5_idx = torch.topk(probs, k=min(5, len(self.class_names)))
        all_preds = [
            {
                "class": self.class_names[i],
                "confidence": float(c)
            }
            for c, i in zip(top5_conf, top5_idx)
        ]
        
        return {
            "disease": top_disease,
            "confidence": round(top_confidence, 4),
            "all_predictions": all_preds,
        }
    
    def predict_batch(self, image_paths: list) -> list:
        """Predict for multiple images."""
        results = []
        for path in image_paths:
            try:
                result = self.predict(image_path=path)
                result["image"] = path
                results.append(result)
            except Exception as e:
                results.append({"image": path, "error": str(e)})
        return results
