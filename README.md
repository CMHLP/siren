# SIREN Data Collection and Analysis Suite

## Scrapers

E-Papers (siren/scrapers/epaper)

- [x] The New Indian Express (readwhere/tnie.py)
- [x] Tribune (readwhere/tribune.py)
- [x] Times Of India (toi.py)
- [x] Mirror (toi.py)
- [x] Hindustan Times (ht.py)
- [x] Telegraph
- [ ] The Hindu
- [x] The Indian Express

Online Publications

- [x] Mirror
- [x] News Minute
- [ ] Telegraph

## Benchmarks

|Device                       |CPU (model, cores+threads, clock)|RAM (size, speed)                                   |GPU (model, vram, clock)|
|-----------------------------|---------------------------------|----------------------------------------------------|------------------------|
|PC                           |Ryzen 7 3700x, 8+16, 4.2GHz      |32GB DDR4 @ 3000MHz                                 |RX 5700 XT, 8GB, 1750MHz|
|Laptop                       |Ryzen 3 3250U, 2+4, 2.6GHz       |6GB DDR4 @ 2400 MHz                                 |none (integrated Vega 3)|
|Raspi 5                      |ARM Cortex A-76, 4+0, 2.4GHz     |8GB DDR4 @ 4267 MHz                                 |VideoCore VII, -, 800MHz|
|Github Actions*              |AMD EPYC 7763, 4, 2.2GHz         |16GB DDR4 @ unknown                                 |none                    |


|Device                       |Pytesseract (Single-threaded)|EasyOCR (Single-threaded)                           |Pytesseract (Multithreaded)|EasyOCR (Multithreaded)|
|-----------------------------|-----------------------------|----------------------------------------------------|---------------------------|-----------------------|
|PC                           |143.14                       |804.62                                              |41                         |564.27                 |
|Laptop                       |933.23                       |1749.2                                              |788.3                      |1592.45                |
|Raspi 5                      |619.41                       |1508.53                                             |461.13                     |1228                   |
|Github Actions               |300                          |1486.82                                             |Process Timeout            |1180.09                |


Interestingly, using too many threads can result in worse performance than a single-threaded run.
This is likely because of the increased context-switching and resource sharing across the threads.
Python's default ThreadPoolExecutor has a default of (min(32, os.cpu_count() + 4) max threads. 
On the PC, this would be 16 threads + 4 = 20 max threads. However, this is not preferable, as the OCR engines are executed
individually on each thread; which is a massive waste of resources. From testing, (os.cpu_count() + 4) // 4
has achieved better results across devices. 

Additionally, none of my devices have a CUDA GPUs; this would significantly improve performance for EasyOCR, which has optional GPU support.

Github Actions also has a 4-core limit as per their documentation. However, while EasyOCR gets a performance benefit from multithreading, pytesseract always seems to cause the process to crash.

There are around 70 seperate editions covered by the scraper suite. Not all of these use OCR, so we should be able to comfortably use Actions for automation.
