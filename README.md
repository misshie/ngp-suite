# **NGPsuite**

*Next-Generation Phenotyping powered by GestaltMatcher and PubCaseFinder*

<img src="./assets/NGPsuite.png" width="85%" alt="NGP suite" />

## **Table of Contents**

1. [Introduction](#introduction)
2. [For End-Users (Installation & Usage)](#for-end-users-installation--usage)  
3. [For Developers](#for-developers)
4. [Technology Stack](#technology-stack)
5. [License](#license)
7. [Acknowledgements](#acknowledgements)  
8. [Author](#author)
9. [References](#references)

----

<p align="center">
  <img src="./assets/ngpsuite-ss1.png" width="30%" alt="NGPsuite screenshot 1" />
  <img src="./assets/ngpsuite-ss2.png" width="30%" alt="NGPsuite screenshot 2" />
  <img src="./assets/ngpsuite-ss3.png" width="30%" alt="NGPsuite screenshot 3" />
</p>
<p align="center"><em>Reference: Cuscó et al., BMC Med Genet 2008, doi:10.1186/1471-2350-9-27, licensed under CC BY 2.0</em></p>

----
## **Introduction**

**NGPsuite** is a web-based application designed to support the diagnosis of rare diseases.
It integrates facial phenotype analysis from images with clinical information (HPO IDs) to provide
a comprehensive view for clinical geneticists and medical researchers.

The application leverages the analytical power of [GestaltMatcher](https://www.gestaltmatcher.org/) for image-based predictions
and complements it with data from [PubCaseFinder](https://pubcasefinder.dbcls.jp/?lang=en) for HPO-based phenotypic analysis, offering a multi-modal
approach to next-generation phenotyping.

***NGPsuite, GestaltMatcher, PubCaseFinder, and external information sources are intended for research and educational purposes only***.

----
## **For End-Users (Installation & Usage)**

This section provides instructions for users who want to run the application.
No front-end development environment is required.

### **Prerequisites**

* Docker must be installed on your system.

### **1. Get the Application**

Download latest release zip file and unzip.

### **2. Required Models and Data**

Due to ethical reasons the pretrained models are not made available publicly. \
Once access has been granted to [GestaltMatcher Database (GMDB)](https://db.gestaltmatcher.org/), the pretrained model weights and annotations can be requested as well.

After obtaining the necessary files, please place them into the correct directories as follows:

1. Pretrained Feature Extractor (Encoder) Models
Place the following files in the `backend/saved_models/` directory:
* `Resnet50_Final.pth` (for face alignment)
* `glint360k_r50.onnx` (base pre-trained model for model a)
* `glint360k_r100.onnx` (base pre-trained model for model b)

2. Trained Feature Space Models (Gallery)
Place the following files in the `backend/saved_models/` directory:
* `s1_glint360k_r50_512d_gmdb__v1.1.2_bs64_size112_channels3_last_model.pth` (model a)
* `s2_glint360k_r100_512d_gmdb__v1.1.2_bs128_size112_channels3_last_model.pth` (model b)

3. Annotations for the Gallery Encodings
Place the following file in the `backend/data/gallery_encodings/` directory:
* `GMDB_gallery_encodings_v1.1.2_service.pkl`

4. Additional data for GestaltMatcher-Arc v1.1.2
Place the following files in the `backend/data/` directory:
* `transformation_probabilities_07052025.csv` (syndrome transformation probabilities for PP4)
* `image_gene_and_syndrome_metadata_pp4_19112025_v112.p` (disorder/gene metadata)

The final file tree should look like this:

```
ngp-suite/
└── backend/
    ├── data/
    │   ├── gallery_encodings/
    │   ├── transformation_probabilities_07052025.csv
    │   └── image_gene_and_syndrome_metadata_pp4_19112025_v112.p
    ├── saved_models/
    └── ... (other backend files)
```

### **3. Build and Run the Application**

Navigate to the backend directory and use Docker Compose to build and start the services.

```
cd backend  
sudo docker compose build  
sudo docker compose up -d     # without `-d`, you can watch logs on console.
```

The initial startup may take about 90 seconds as the API service loads the models.

### **4. Access the Application**

Once the startup process is complete, open your web browser and navigate to:  
`https://localhost`

#### **Security Warning on First Access**

When you first access *NGPsuite*, your browser may show a potential security warning due to our use of a self-signed certificate. This is a normal and expected behavior. To proceed, please click on the button labeled "Advanced" or "Proceed to..." and accept the certificate.

## **For Developers**

This section is for developers who wish to contribute to the project.

### **Initial Setup**

1. **Frontend Dependencies:**
```
   cd frontend  
   npm install
```

2. Backend Data:  
   Follow step 2 in the "For End-Users" section to place the required trained models in the backend directory.

### **Running in Development Mode**

1. **Start Frontend Dev Server:**
```
   cd frontend  
   npm run dev
```

2. Start Backend API Server:  
```
   In a separate terminal:  
   cd backend  
   sudo docker compose up --build
```

   The frontend will now be available at `http://localhost:3000` with hot-reloading enabled,
   and it will communicate with the API server running inside Docker.

### **Building the Frontend**

To build the production-ready frontend and copy it to the backend's static directory,
run the provided script from the project root:

`./build-frontend.sh`

## **Technology Stack**

* **Frontend:** [![Vue.js 3](https://img.shields.io/badge/Vue.js-3-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Pinia](https://img.shields.io/badge/pinia-%23F8E035.svg?style=for-the-badge&logo=pinia&logoColor=black)](https://pinia.vuejs.org/)
[![vue-i18n](https://img.shields.io/badge/vue--i18n-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://github.com/intlify/vue-i18n-next)
[![Axios](https://img.shields.io/badge/Axios-5A29E4?style=for-the-badge&logo=axios&logoColor=white)](https://github.com/axios/axios)
[![Vuetify](https://img.shields.io/badge/Vuetify-1867C0?style=for-the-badge&logo=vuetify&logoColor=white)](https://vuetifyjs.com/)
[![FilePond](https://img.shields.io/badge/FilePond-000000?style=for-the-badge&logo=filepond&logoColor=white)](https://pqina.nl/filepond/)
* **Backend:** [![Python 3](https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
* **Infrastructure:** [![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)](https://www.nginx.com/)

## **License**

[![Creative Commons License](https://i.creativecommons.org/l/by-nc/4.0/88x31.png)](http://creativecommons.org/licenses/by-nc/4.0/)


This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License**.
See the [LICENSE.md](LICENSE.md) file for full details.

## **Acknowledgements**

The backend service of this project is based on the work of
[GestaltMatcher](https://www.gestaltmatcher.org/) with their [repository](https://github.com/igsb/GestaltMatcher-Arc/).
The backend service utilizes the API of PubCaseFinder; see [detailed description](https://pubcasefinder.dbcls.jp/api). The author is grateful for their foundational contributions to the field.

We would like to thank all participants and organizers of the [DBCLS BioHackathon 2025](https://2025.biohackathon.org/) (September 14-20, 2025, Mie, Japan) for their valuable discussions and support, which contributed significantly to the development of this project.

## **Author**

* **Hiroyuki Mishima** (三嶋 博之)*
* Department of Human Genetics, Atomic Bomb Disease Institute, Nagasaki University*  
* [Research Map Profile](https://researchmap.jp/misshie?lang=en)

## References
### GestaltMatcher
1. **GestaltMatcher**: Hsieh, T.-C. et al. (2022). GestaltMatcher facilitates rare disease matching using facial phenotype descriptors. Nature Genetics, 54(3), 349-357. [https://www.nature.com/articles/s41588-021-01010-x](https://www.nature.com/articles/s41588-021-01010-x)
2. **GestaltMatcher-Arc**: Hustinx, A. et al. (2023). Improving deep facial phenotyping for ultra-rare disorder verification using model ensembles. 2023 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV). doi:[10.1109/wacv56688.2023.00499](https://openaccess.thecvf.com/content/WACV2023/papers/Hustinx_Improving_Deep_Facial_Phenotyping_for_Ultra-Rare_Disorder_Verification_Using_Model_WACV_2023_paper.pdf)
3. **GestaltMatcher Database**: Lesmann, H. et al. (2024). GestaltMatcher Database - A global reference for facial phenotypic variability in rare human diseases. medRxiv. doi:[10.1101/2023.06.06.23290887](https://www.medrxiv.org/content/10.1101/2023.06.06.23290887v3)

### PubCaseFinder
1. Shin, J., Fujiwara, T., Saitsu, H., & Yamaguchi, A. (2025).Ontology-based expansion of virtual gene panels to improve diagnostic efficiency for rare genetic diseases. BMC medical informatics and decision making, 25(Suppl 1), 59. doi:[10.1186/s12911-025-02910-2](https://doi.org/10.1186/s12911-025-02910-2)
2. Fujiwara, T., Shin, J. M., & Yamaguchi, A. (2022). Advances in the development of PubCaseFinder, including the new application programming interface and matching algorithm. Human mutation, 10.1002/humu.24341. Advance online publication. doi:[10.1002/humu.24341](https://doi.org/10.1002/humu.24341)
3. Yamaguchi, A., Shin, J. M., & Fujiwara, T. (2021, December). Gene Ranking based on Paths from Phenotypes to Genes on Knowledge Graph. In The 10th International Joint Conference on Knowledge Graphs (pp. 131-134). doi:[10.1145/3502223.3502240](https://doi.org/10.1145/3502223.3502240)
4. Fujiwara, T., Yamamoto, Y., Kim, J. D., Buske, O., & Takagi, T. (2018). PubCaseFinder: A case-report-based, phenotype-driven differential-diagnosis system for rare diseases. The American Journal of Human Genetics, 103(3), 389-399. doi:[10.1016/j.ajhg.2018.08.003](https://doi.org/10.1016/j.ajhg.2018.08.003)
