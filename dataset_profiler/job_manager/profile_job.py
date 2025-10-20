import uuid

import ray

from dataset_profiler.schemas.specification import ProfileSpecificationEndpoint
from dataset_profiler.job_manager.job_storing import store_job_status, JobStatus, store_job_response, \
    ProfilesResponse
from dataset_profiler.profile_models import DatasetProfile

def endpoint_specification_to_dataset(specification: ProfileSpecificationEndpoint) -> dict:
    return {
        "id": str(specification.id),
        "citeAs": specification.cite_as,
        "country": specification.country,
        "dataPath": specification.data_uri,
        "datePublished": specification.date_published,
        "description": specification.description,
        "fieldOfScience": specification.fields_of_science,
        "headline": specification.headline,
        "inLanguage": specification.languages,
        "keywords": specification.keywords,
        "license": specification.license,
        "name": specification.name,
        "url": specification.published_url,
        "access": "NOT IMPLEMENTED",
        "uploadedBy": specification.uploaded_by,
    }


@ray.remote
def profile_job(job_id: str, specification: dict, only_light_profile: bool = False) -> None:
    store_job_status(job_id, status=JobStatus.STARTING)
    profile = DatasetProfile(specification)

    # Calculate the light profile (dataset head, dataset distributions)
    profile.extract_distributions()
    light_profile = profile.to_dict_light()
    store_job_response(job_id, ProfilesResponse(
        moma_profile_light=light_profile,
        moma_profile_heavy={},
        cdd_profile={},
    ))
    store_job_status(job_id, status=JobStatus.LIGHT_PROFILE_READY)

    # Calculate the heavy profiles (record sets, cdd profile)
    if only_light_profile:
        return None

    profile.extract_record_sets()
    heavy_profile = profile.to_dict()
    store_job_response(job_id, ProfilesResponse(
        moma_profile_light=light_profile,
        moma_profile_heavy=heavy_profile,
        cdd_profile={},
    ))
    store_job_status(job_id, status=JobStatus.HEAVY_PROFILES_READY)

    return None


if __name__ == "__main__":
    spec = endpoint_specification_to_dataset(
        ProfileSpecificationEndpoint(
            id=uuid.UUID("8930240b-a0e8-46e7-ace8-aab2b42fcc01"),
            cite_as="",
            country="PT",
            data_uri="tests/assets/mathe_assessment/data/",
            date_published="24-05-2025",
            description="This dataset was extracted from the MathE platform, an online educational platform developed to support mathematics teaching and learning in higher education. It contains 546 student responses to questions on several mathematical topics. Each record corresponds to an individual answer and includes the following features: Student ID, Student Country, Question ID, Type of Answer (correct or incorrect), Question Level (basic or advanced based on the assessment of the contributing professor), Math Topic (broader mathematical area of the question), Math Subtopic, and Question Keywords. The data spans from February 2019 to December 2023.",
            fields_of_science=[
                "MATHEMATICS"
            ],
            headline="Dataset for Assessing Mathematics Learning in Higher Education.",
            languages=[
                "en"
            ],
            keywords=[
                "math",
                "student",
                "higher education"
            ],
            license="CC0 1.0",
            name="Mathematics Learning Assessment",
            published_url="https://dados.ipb.pt//dataset.xhtml?persistentId=doi:10.34620/dadosipb/PW3OWY",
            uploaded_by="ADMIN"
        )
    )
    profile_job("test_job_id", spec)
