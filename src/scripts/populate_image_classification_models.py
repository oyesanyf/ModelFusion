#!/usr/bin/env python3
"""
Populate Image Classification Models in Database
This script adds comprehensive image classification models to the HuggingFace model database
for integration with the Sagamu AI orchestrator system.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Image classification models to add to the database
IMAGE_CLASSIFICATION_MODELS = [
    {
        "model_id": "google/vit-base-patch16-224",
        "author": "google",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "vit", "transformer"],
        "description": "Vision Transformer (ViT) model for image classification. Pre-trained on ImageNet-21k and fine-tuned on ImageNet-1k.",
        "downloads": 5000000,
        "likes": 1500,
        "last_modified": "2024-01-15T10:30:00Z",
        "license": "apache-2.0",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "vit",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 330
    },
    {
        "model_id": "microsoft/resnet-50",
        "author": "microsoft",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "resnet", "cnn"],
        "description": "ResNet-50 model for image classification. Pre-trained on ImageNet-1k with residual connections.",
        "downloads": 8000000,
        "likes": 2200,
        "last_modified": "2024-02-20T14:15:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "resnet",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 98
    },
    {
        "model_id": "facebook/convnext-base-224",
        "author": "facebook",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "convnext", "cnn"],
        "description": "ConvNeXt-Base model for image classification. Modern CNN architecture with improved performance.",
        "downloads": 1200000,
        "likes": 800,
        "last_modified": "2024-03-10T09:45:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "convnext",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 88
    },
    {
        "model_id": "microsoft/swin-base-patch4-window7-224",
        "author": "microsoft",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "swin", "transformer"],
        "description": "Swin Transformer Base model for image classification. Hierarchical vision transformer with shifted windows.",
        "downloads": 2500000,
        "likes": 1200,
        "last_modified": "2024-01-25T16:20:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "swin",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 193
    },
    {
        "model_id": "timm/efficientnet_b3",
        "author": "timm",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "efficientnet", "cnn"],
        "description": "EfficientNet-B3 model for image classification. Optimized CNN architecture for efficiency and accuracy.",
        "downloads": 1800000,
        "likes": 950,
        "last_modified": "2024-02-05T11:30:00Z",
        "license": "apache-2.0",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "efficientnet",
        "input_size": 300,
        "num_classes": 1000,
        "model_size_mb": 12
    },
    {
        "model_id": "google/vit-large-patch16-224",
        "author": "google",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "vit", "transformer", "large"],
        "description": "Large Vision Transformer (ViT) model for high-accuracy image classification.",
        "downloads": 3000000,
        "likes": 1100,
        "last_modified": "2024-01-20T13:45:00Z",
        "license": "apache-2.0",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "vit",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 1096
    },
    {
        "model_id": "facebook/deit-base-distilled-patch16-224",
        "author": "facebook",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "deit", "transformer", "distillation"],
        "description": "Data-efficient image transformer (DeiT) with knowledge distillation for efficient training.",
        "downloads": 900000,
        "likes": 600,
        "last_modified": "2024-02-15T08:30:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "deit",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 86
    },
    {
        "model_id": "microsoft/beit-base-patch16-224-pt22k-ft22k",
        "author": "microsoft",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "beit", "transformer"],
        "description": "BEiT (BERT pre-training of Image Transformers) for self-supervised vision representation learning.",
        "downloads": 700000,
        "likes": 450,
        "last_modified": "2024-03-05T12:15:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "beit",
        "input_size": 224,
        "num_classes": 21841,
        "model_size_mb": 86
    },
    {
        "model_id": "facebook/regnet-y-040",
        "author": "facebook",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "regnet", "cnn"],
        "description": "RegNet-Y-040 model for image classification. Design space exploration for CNN architectures.",
        "downloads": 500000,
        "likes": 300,
        "last_modified": "2024-01-30T15:20:00Z",
        "license": "mit",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition"],
        "architecture": "regnet",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 21
    },
    {
        "model_id": "google/mobilenet_v2_1.0_224",
        "author": "google",
        "pipeline_tag": "image-classification",
        "tags": ["vision", "image-classification", "mobilenet", "cnn", "mobile"],
        "description": "MobileNetV2 model optimized for mobile and edge devices with efficient depthwise convolutions.",
        "downloads": 4000000,
        "likes": 1800,
        "last_modified": "2024-02-10T10:45:00Z",
        "license": "apache-2.0",
        "task_keywords": ["image-classification", "vision", "computer-vision", "object-recognition", "mobile"],
        "architecture": "mobilenet",
        "input_size": 224,
        "num_classes": 1000,
        "model_size_mb": 14
    }
]

def calculate_model_scores(model_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate decision scores for image classification models."""
    
    # Base scores
    popularity_score = min(1.0, model_data["downloads"] / 10000000)  # Normalize to 10M downloads
    recency_score = 0.8  # Most models are recent
    
    # Architecture-specific scores
    architecture_scores = {
        "vit": 0.9,      # High accuracy, modern
        "resnet": 0.85,  # Proven, reliable
        "convnext": 0.88, # Modern, efficient
        "swin": 0.92,    # State-of-the-art
        "efficientnet": 0.87, # Efficient
        "deit": 0.86,    # Data-efficient
        "beit": 0.89,    # Self-supervised
        "regnet": 0.84,  # Well-designed
        "mobilenet": 0.83 # Mobile-optimized
    }
    
    capability_score = architecture_scores.get(model_data.get("architecture", "unknown"), 0.8)
    
    # Efficiency score based on model size
    model_size_mb = model_data.get("model_size_mb", 100)
    efficiency_score = max(0.5, 1.0 - (model_size_mb / 1000))  # Smaller is better
    
    # Decision score (weighted combination)
    decision_score = (
        popularity_score * 0.3 +
        capability_score * 0.4 +
        efficiency_score * 0.2 +
        recency_score * 0.1
    )
    
    return {
        "decision_score": decision_score,
        "capability_score": capability_score,
        "efficiency_score": efficiency_score,
        "popularity_score": popularity_score
    }

def populate_image_classification_models(db_path: str = "db/hf_models.db"):
    """Populate the database with image classification models."""
    
    # Ensure database directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if models table exists, create if not
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                author TEXT,
                pipeline_tag TEXT,
                tags TEXT,
                description TEXT,
                downloads INTEGER,
                likes INTEGER,
                last_modified TEXT,
                license TEXT,
                task_keywords TEXT,
                decision_score REAL,
                capability_score REAL,
                efficiency_score REAL,
                popularity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add additional columns for image classification specific data
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN architecture TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN input_size INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN num_classes INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN model_size_mb REAL')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Insert or update image classification models
        for model_data in IMAGE_CLASSIFICATION_MODELS:
            scores = calculate_model_scores(model_data)
            
            cursor.execute('''
                INSERT OR REPLACE INTO models 
                (model_id, author, pipeline_tag, tags, description, downloads, likes, 
                 last_modified, license, task_keywords, decision_score, capability_score, 
                 efficiency_score, popularity_score, architecture, input_size, num_classes, 
                 model_size_mb, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                model_data["model_id"],
                model_data["author"],
                model_data["pipeline_tag"],
                json.dumps(model_data["tags"]),
                model_data["description"],
                model_data["downloads"],
                model_data["likes"],
                model_data["last_modified"],
                model_data["license"],
                json.dumps(model_data["task_keywords"]),
                scores["decision_score"],
                scores["capability_score"],
                scores["efficiency_score"],
                scores["popularity_score"],
                model_data.get("architecture"),
                model_data.get("input_size"),
                model_data.get("num_classes"),
                model_data.get("model_size_mb")
            ))
        
        # Add task-model mappings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_tasks (
                model_id TEXT,
                task_type TEXT,
                confidence REAL,
                PRIMARY KEY (model_id, task_type),
                FOREIGN KEY (model_id) REFERENCES models (model_id)
            )
        ''')
        
        # Add image classification task mappings
        for model_data in IMAGE_CLASSIFICATION_MODELS:
            cursor.execute('''
                INSERT OR REPLACE INTO model_tasks (model_id, task_type, confidence)
                VALUES (?, ?, ?)
            ''', (model_data["model_id"], "image-classification", 0.95))
            
            # Add related tasks
            cursor.execute('''
                INSERT OR REPLACE INTO model_tasks (model_id, task_type, confidence)
                VALUES (?, ?, ?)
            ''', (model_data["model_id"], "object-recognition", 0.9))
            
            cursor.execute('''
                INSERT OR REPLACE INTO model_tasks (model_id, task_type, confidence)
                VALUES (?, ?, ?)
            ''', (model_data["model_id"], "computer-vision", 0.85))
        
        conn.commit()
        
        print(f"✅ Successfully populated {len(IMAGE_CLASSIFICATION_MODELS)} image classification models")
        
        # Verify the data
        cursor.execute('SELECT COUNT(*) FROM models WHERE pipeline_tag = "image-classification"')
        count = cursor.fetchone()[0]
        print(f"📊 Total image classification models in database: {count}")
        
        # Show top models by decision score
        cursor.execute('''
            SELECT model_id, decision_score, 
                   COALESCE(architecture, 'Unknown') as architecture,
                   COALESCE(model_size_mb, 0) as model_size_mb 
            FROM models 
            WHERE pipeline_tag = "image-classification" 
            ORDER BY decision_score DESC 
            LIMIT 5
        ''')
        
        print("\n🏆 Top 5 Image Classification Models by Decision Score:")
        for row in cursor.fetchall():
            print(f"  • {row[0]} (Score: {row[1]:.3f}, Arch: {row[2]}, Size: {row[3]}MB)")

def main():
    """Main function to populate image classification models."""
    print("🖼️ Populating Image Classification Models in Database")
    print("=" * 60)
    
    db_path = "db/hf_models.db"
    populate_image_classification_models(db_path)
    
    print("\n✅ Image classification models successfully integrated into database!")
    print("   The models are now available for dynamic selection in the Sagamu AI orchestrator.")

if __name__ == "__main__":
    main() 