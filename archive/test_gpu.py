import torch

def test_gpu():
    print(torch.cuda.is_available())
    print(torch.cuda.device_count())
    print(torch.cuda.get_device_name(0))
    print(torch.cuda.current_device())

if __name__ == '__main__':
    test_gpu()