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
<p align="center"><em>Image from Dr. Ibrahim Abdelrazek at GestaltMatcher Database https://db.gestaltmatcher.org/patients/15727</em></p>

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

> **Breaking change:** the Docker image no longer contains the GMDB models, gallery encodings, or metadata.
> They are **mounted read-only from a directory on your machine** when the container starts, so patient-derived
> data never enters the image. Changing the data does not require rebuilding the image.

Create a directory for the GMDB files, preferably **outside** this repository (for example `~/ngpsuite-gmdb`),
with `data/` and `saved_models/` subdirectories. Its location is given by the `NGPSUITE_GMDB_DIR` variable
(see [step 3](#3-build-and-run-the-application)). After obtaining the necessary files, place them as follows:

1. Pretrained Feature Extractor (Encoder) Models
Place the following files in `$NGPSUITE_GMDB_DIR/saved_models/`:
* `Resnet50_Final.pth` (for face alignment)
* `glint360k_r100.onnx` (base pre-trained model for model b and the third encoder)

2. Trained Feature Space Models (Gallery)
Place the following files in `$NGPSUITE_GMDB_DIR/saved_models/`:
* `s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth` (model a)
* `s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth` (model b)

3. Annotations for the Gallery Encodings
Place the following file in `$NGPSUITE_GMDB_DIR/data/gallery_encodings/`:
* `GMDB_gallery_encodings_23052026_v1.1.4_service.pkl`

4. Additional data for GestaltMatcher-Arc v1.1.4
Place the following files in `$NGPSUITE_GMDB_DIR/data/`:
* `transformation_probabilities_07052025.csv` (syndrome transformation probabilities for PP4)
* `patient_metadata_2026-05-23_mondo.p` (disorder/gene metadata, disorders keyed by MONDO ID)

All seven files above are required. The API checks them at startup and stops immediately, listing every missing or unreadable file.

5. MONDO ontology (shipped with the repository)
The following file is tracked under `backend/mondo/` (no patient data) and does not need to be downloaded separately:
* `mondo-international.obo.gz` (labels and ancestor hierarchy for gallery disorders)

This product includes the Mondo Disease Ontology (Mondo) international edition ([mondo.monarchinitiative.org](https://mondo.monarchinitiative.org/)). Mondo's license is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See also [Acknowledgements](#acknowledgements).

The final file trees should look like this:

```
~/ngpsuite-gmdb/                 # = $NGPSUITE_GMDB_DIR (outside the repository, mounted read-only)
├── data/
│   ├── gallery_encodings/
│   │   └── GMDB_gallery_encodings_23052026_v1.1.4_service.pkl
│   ├── transformation_probabilities_07052025.csv
│   └── patient_metadata_2026-05-23_mondo.p
└── saved_models/
    ├── Resnet50_Final.pth
    ├── glint360k_r100.onnx
    ├── s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth
    └── s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth

ngp-suite/
└── backend/
    ├── mondo/                   # shipped in the image
    │   └── mondo-international.obo.gz
    └── ... (other backend files)
```

### **3. Build and Run the Application**

Navigate to the backend directory, tell Docker Compose where your GMDB files are, then build and start the services.

```
cd backend
cp .env.example .env          # then edit .env: NGPSUITE_GMDB_DIR=/absolute/path/to/ngpsuite-gmdb
                              # (credentials and LAN sharing are optional, see "5. Authentication")
docker compose build          # builds the code image only; no GMDB data is included
docker compose up -d          # without `-d`, you can watch logs on console.
```

(On Linux, prefix the `docker` commands with `sudo` if your user is not in the `docker` group.)

The initial startup may take about 90 seconds as the API service loads the models.
If a required file is missing, the `api` container exits right away and prints every missing file
(`docker compose logs api`).

To update the models or data, replace the files under `$NGPSUITE_GMDB_DIR` and run `docker compose restart api`.
No rebuild is needed.

<details>
<summary><strong>Upgrading from v0.2.0 or earlier (data baked into the image)</strong></summary>

Earlier versions required `backend/data/` and `backend/saved_models/` at build time and copied them into the image.
Choose one of the following:

* **Recommended:** move `backend/data/` and `backend/saved_models/` to a directory outside the repository (for example `~/ngpsuite-gmdb`) and set `NGPSUITE_GMDB_DIR` to it in `backend/.env`.
* **Keep the current layout:** leave the files in `backend/data/` and `backend/saved_models/` and do not create `backend/.env`. `NGPSUITE_GMDB_DIR` then defaults to `backend/`.

Then rebuild once. The old image and its build cache still contain the GMDB files, so remove them:

```
docker compose down
docker image rm backend-api:latest
docker builder prune
```

</details>

#### **GPU / CUDA note**

The Docker deployment of NGPsuite (Web API) runs on **CPU**. It does **not** use a GPU for inference, even if one is present on the host. End users do not need CUDA, NVIDIA drivers, or any GPU-related setup.

<details>
<summary><strong>For developers: optional CUDA-enabled image build</strong></summary>

By default, the API image installs **CPU-only** PyTorch (smaller image, no NVIDIA package dependencies).

If you intentionally want a CUDA-enabled PyTorch install inside the image (for experiments or future GPU work), build with:

```
cd backend
docker compose build --build-arg USE_CUDA=1
# optional: also rebuild without cache
# docker compose build --no-cache --build-arg USE_CUDA=1
```

Notes:

* This only changes which PyTorch wheels are installed. The current Web API still runs inference on CPU unless the application code is changed to use CUDA.
* The CUDA build is larger, slower, and needs more disk space during `pip install`.
* Using a GPU at runtime additionally requires NVIDIA drivers and the NVIDIA Container Toolkit on the host; that is separate from this build flag.

Requirements files:

* `backend/requirements_docker.txt` — shared deps for the default (CPU) build; PyTorch / torchvision are installed from the official CPU wheel index in the Dockerfile
* `backend/requirements_docker_cuda.txt` — same deps plus `torch` for the CUDA opt-in build

The Dockerfile pins `torch==2.3.1` and `torchvision==0.18.1` with a pip constraints file so other packages cannot upgrade them to a CUDA build from PyPI.

</details>

### **4. Access the Application**

Once the startup process is complete, open your web browser and navigate to:  
`https://localhost`
(or `https://localhost:<NGPSUITE_PORT>` if you changed the port in `backend/.env`).

#### **macOS: port 443 and Docker Desktop**

Publishing `127.0.0.1:443` on macOS requires Docker Desktop's privileged helper. Enable
**Settings > Advanced > Allow privileged port mapping** and restart Docker Desktop. Without it, `nginx` fails to start with
`failed to connect to /var/run/com.docker.vmnetd.sock`. If you cannot enable it, set an unprivileged port in `backend/.env`
and open `https://localhost:8443`:

```
NGPSUITE_PORT=8443
```

Linux and Windows do not need this.

#### **Security Warning on First Access**

When you first access *NGPsuite*, your browser may show a potential security warning due to our use of a self-signed certificate. This is a normal and expected behavior. To proceed, please click on the button labeled "Advanced" or "Proceed to..." and accept the certificate.

### **5. Authentication**

`POST /api/predict` is protected by HTTP Basic authentication. Out of the box the credentials are the placeholders
`your_username` / `your_password`, which are also the defaults of the web UI, so the application works without any setup.
Because these values are public, **the placeholders provide no real protection**. That is acceptable while the service is
reachable only from your own machine, which is the default: the service is published on `127.0.0.1` (port 443, or `NGPSUITE_PORT`).
At startup the `api` container prints a notice (`docker compose logs api`) while the placeholders are in use.

The service is intended for your own machine or a trusted LAN. Do not expose it to the internet.

**Changing the credentials.** Set them in `backend/.env`, then apply with `docker compose up -d`:

```
NGPSUITE_USERNAME=your-name
NGPSUITE_PASSWORD=a-long-password
```

Enter the same values in the web UI under **Settings**. The credentials are passed to the container as environment
variables; they are not stored in the image.

**Sharing on your LAN.** Set `NGPSUITE_BIND=0.0.0.0` in `backend/.env` and run `docker compose up -d`.
The response of `/api/predict` contains information derived from GMDB patients, so change the credentials first.
If you share the service while the placeholders are still in use, the `api` log shows a prominent warning
(the service still starts).

<details>
<summary><strong>Upgrading from the previous release (config.json, port 443)</strong></summary>

* `backend/config.json` is no longer used or shipped. If you had changed its values, put them in `backend/.env` as
  `NGPSUITE_USERNAME` / `NGPSUITE_PASSWORD` and rebuild once (`docker compose build`).
* Port 443 is now published on `127.0.0.1` only. If other machines on your LAN connected to the service, set
  `NGPSUITE_BIND=0.0.0.0` in `backend/.env`. The host port can be changed with `NGPSUITE_PORT` (see the macOS note above).

</details>

## **For Developers**

This section is for developers who wish to contribute to the project.

### **Initial Setup**

1. **Frontend Dependencies:**
```
   cd frontend  
   npm install
```

2. Backend Data:  
   Follow steps 2 and 3 in the "For End-Users" section: place the GMDB files in a directory of your own and
   point `NGPSUITE_GMDB_DIR` (in `backend/.env`) to it. They are mounted into the container, not copied into it.

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
   docker compose up --build
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

`backend/lib/` includes third-party code (Pytorch_Retinaface, ssd.pytorch, object-detection.torch, Fast R-CNN, InsightFace). That code is not covered by CC BY-NC 4.0 and remains under its original license (MIT or BSD-2-Clause). See [backend/THIRD_PARTY_NOTICES.md](backend/THIRD_PARTY_NOTICES.md) for copyright notices and full license texts; the Docker image ships it as `/app/THIRD_PARTY_NOTICES.md`.

## **Acknowledgements**

The backend service of this project is based on the work of
[GestaltMatcher](https://www.gestaltmatcher.org/) with their [repository](https://github.com/igsb/GestaltMatcher-Arc/).
The backend service utilizes the API of PubCaseFinder; see [detailed description](https://pubcasefinder.dbcls.jp/api). The author is grateful for their foundational contributions to the field.
Face detection and alignment use code from [Pytorch_Retinaface](https://github.com/biubug6/Pytorch_Retinaface) and [InsightFace](https://github.com/deepinsight/insightface).

This product includes the Mondo Disease Ontology (Mondo) international edition
([mondo.monarchinitiative.org](https://mondo.monarchinitiative.org/)). Mondo's license is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The ontology file is shipped under `backend/mondo/`.

We would like to thank all participants and organizers of the [DBCLS BioHackathon 2025](https://2025.biohackathon.org/) (September 14-20, 2025, Mie, Japan) and [DBCLS BioHackathon 2026](https://2026.biohackathon.org/) (September 13-19, 2026, Ehime, Japan) for their valuable discussions and support, which contributed significantly to the development of this project.

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
