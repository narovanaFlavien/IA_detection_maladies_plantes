from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights


IMAGE_SIZE = 224

weights = EfficientNet_B0_Weights.DEFAULT

mean = weights.transforms().mean
std = weights.transforms().std


inference_transform  = transforms.Compose([
    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=mean,
        std=std
    )
])