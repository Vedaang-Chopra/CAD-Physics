# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/db/utilities/db_handler.py
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slugify_identifier(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]", "_", str(value)).strip("_").lower()
    return re.sub(r"_+", "_", slug)


@dataclass(frozen=True)
class GenerationTarget:
    """Logical generation target encoded as columns in the canonical schema."""

    model_name: str
    pipeline_variant: str = "baseline"

    @property
    def table_name(self) -> str:
        if self.pipeline_variant == "baseline":
            return f"generations_{self.model_name}"
        return f"generations_{self.model_name}_{self.pipeline_variant}"

    @property
    def __tablename__(self) -> str:
        return self.table_name


def parse_generation_table_name(table_name: str) -> GenerationTarget:
    """Map a legacy generations_* name into canonical model/pipeline columns."""
    slug = _slugify_identifier(table_name)
    while slug.startswith("generations_"):
        slug = slug[len("generations_") :]

    suffix_map = (
        ("_rag_rag_fixed", "rag_fixed"),
        ("_rag_fixed", "rag_fixed"),
        ("_rag_rag", "rag"),
        ("_rag", "rag"),
    )
    for suffix, pipeline_variant in suffix_map:
        if slug.endswith(suffix):
            return GenerationTarget(slug[: -len(suffix)], pipeline_variant)

    return GenerationTarget(slug, "baseline")

# --- Database Models ---

class MasterMetadata(Base):
    """Table 1: ID, Prompts, Ground Truth Stats (Shared across all models)"""
    __tablename__ = 'master_metadata'
    
    id = Column(String, primary_key=True) # Directory name (e.g., "00000007")
    
    expert_prompt = Column(Text)
    non_expert_prompt = Column(Text)
    
    # Storing Ground_Truth.json content as structured JSONB
    ground_truth_stats = Column(JSONB)
    
    # Relationships
    geometry = relationship("GroundTruthGeometry", back_populates="master", uselist=False)
    results = relationship("ModelGeneration", back_populates="master")
    entities = relationship("CadEntity", back_populates="master")
    stratification = relationship("StratificationData", back_populates="master", uselist=False)
    ground_truth_code = relationship("GroundTruthCode", back_populates="master", uselist=False)

class GroundTruthGeometry(Base):
    """Table 2: ID, GT STL, GT OBJ (Shared across all tests)"""
    __tablename__ = 'ground_truth_geometry'
    
    id = Column(String, ForeignKey('master_metadata.id'), primary_key=True)
    
    stl_content = Column(LargeBinary)
    obj_content = Column(LargeBinary)
    
    master = relationship("MasterMetadata", back_populates="geometry")

class ModelGeneration(Base):
    """
    Canonical generation run table.

    One row = one attempt for one dataset item, model, prompt variant, and
    pipeline variant. Large payloads live in one-to-one child tables.
    """
    __tablename__ = 'model_generations'

    generation_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(String, ForeignKey('master_metadata.id'), nullable=False)
    model_name = Column(Text, nullable=False)
    prompt_variant = Column(Text, nullable=False)
    pipeline_variant = Column(Text, nullable=False)
    status = Column(Text)
    source_generation_id = Column(BigInteger, ForeignKey('model_generations.generation_id'))
    source_table_name = Column(Text)
    legacy_unique_id = Column(Integer)
    migration_batch = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "prompt_variant IN ('expert', 'non_expert')",
            name="chk_model_generations_prompt_variant",
        ),
        UniqueConstraint(
            "dataset_id",
            "model_name",
            "prompt_variant",
            "pipeline_variant",
            name="uq_model_generations_logical_slot",
        ),
        UniqueConstraint(
            "source_table_name",
            "legacy_unique_id",
            "prompt_variant",
            name="uq_model_generations_source_legacy_prompt",
        ),
    )

    master = relationship("MasterMetadata", back_populates="results")
    source_generation = relationship("ModelGeneration", remote_side=[generation_id])
    code = relationship(
        "ModelGenerationCode",
        back_populates="generation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    artifacts = relationship(
        "ModelGenerationArtifacts",
        back_populates="generation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    evaluation = relationship(
        "ModelGenerationEvaluation",
        back_populates="generation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ModelGenerationCode(Base):
    """One-to-one generated source payload for a canonical generation."""
    __tablename__ = 'model_generation_code'

    generation_id = Column(
        BigInteger,
        ForeignKey('model_generations.generation_id', ondelete='CASCADE'),
        primary_key=True,
    )
    generated_code = Column(Text)
    raw_response = Column(Text)
    traceback = Column(Text)

    generation = relationship("ModelGeneration", back_populates="code")


class ModelGenerationArtifacts(Base):
    """One-to-one artifact payload for a canonical generation."""
    __tablename__ = 'model_generation_artifacts'

    generation_id = Column(
        BigInteger,
        ForeignKey('model_generations.generation_id', ondelete='CASCADE'),
        primary_key=True,
    )
    generated_stl = Column(LargeBinary)
    artifact_hash = Column(Text)

    generation = relationship("ModelGeneration", back_populates="artifacts")


class ModelGenerationEvaluation(Base):
    """One-to-one primary evaluation payload for a canonical generation."""
    __tablename__ = 'model_generation_evaluations'

    generation_id = Column(
        BigInteger,
        ForeignKey('model_generations.generation_id', ondelete='CASCADE'),
        primary_key=True,
    )
    metrics = Column(JSONB)
    primary_label = Column(Text)
    secondary_flags = Column(JSONB)
    reason_short = Column(Text)
    evidence = Column(JSONB)
    confidence = Column(Float)
    evaluated_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    generation = relationship("ModelGeneration", back_populates="evaluation")


class StratificationData(Base):
    """Auxiliary Table: Stratification Data from Excel"""
    __tablename__ = 'stratification_data'
    
    id = Column(String, ForeignKey('master_metadata.id'), primary_key=True)
    simple = Column(Boolean)
    moderate = Column(Boolean)
    complex = Column(Boolean)
    very_complex = Column(Boolean)
    semantic_complexity = Column(String)
    mesh_complexity = Column(String)
    compilation_difficulty = Column(String)
    
    master = relationship("MasterMetadata", back_populates="stratification")


class CadEntity(Base):
    """Detailed CAD entities parsed from <dataset_id>.json."""
    __tablename__ = 'cad_entities'

    unique_id = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String, ForeignKey('master_metadata.id'))
    entity_key = Column(String)
    name = Column(String)
    type = Column(String)
    data = Column(JSONB)

    master = relationship("MasterMetadata", back_populates="entities")


class GroundTruthCode(Base):
    """Ground-truth Python code for each dataset item."""
    __tablename__ = 'ground_truth_code'

    id = Column(String, ForeignKey('master_metadata.id'), primary_key=True)
    python_code = Column(Text)

    master = relationship("MasterMetadata", back_populates="ground_truth_code")


def _generation_slot_query(
    session,
    *,
    dataset_id: str,
    model_name: str,
    prompt_variant: str,
    pipeline_variant: str,
):
    return (
        session.query(ModelGeneration)
        .filter_by(
            dataset_id=dataset_id,
            model_name=model_name,
            prompt_variant=prompt_variant,
            pipeline_variant=pipeline_variant,
        )
        .order_by(
            ModelGeneration.updated_at.desc(),
            ModelGeneration.created_at.desc(),
            ModelGeneration.generation_id.desc(),
        )
    )


def _collapse_generation_slot_duplicates(session, survivor: ModelGeneration) -> int:
    duplicates = (
        _generation_slot_query(
            session,
            dataset_id=survivor.dataset_id,
            model_name=survivor.model_name,
            prompt_variant=survivor.prompt_variant,
            pipeline_variant=survivor.pipeline_variant,
        )
        .filter(ModelGeneration.generation_id != survivor.generation_id)
        .all()
    )
    if not duplicates:
        return 0

    duplicate_ids = [dup.generation_id for dup in duplicates]
    session.query(ModelGeneration).filter(
        ModelGeneration.source_generation_id.in_(duplicate_ids),
        ModelGeneration.generation_id != survivor.generation_id,
    ).update(
        {ModelGeneration.source_generation_id: survivor.generation_id},
        synchronize_session=False,
    )

    if survivor.source_generation_id in duplicate_ids:
        survivor.source_generation_id = None

    for dup in duplicates:
        session.delete(dup)

    return len(duplicates)


def _get_or_create_generation_slot(
    session,
    *,
    dataset_id: str,
    model_name: str,
    prompt_variant: str,
    pipeline_variant: str,
    now: datetime,
) -> ModelGeneration:
    record = (
        _generation_slot_query(
            session,
            dataset_id=dataset_id,
            model_name=model_name,
            prompt_variant=prompt_variant,
            pipeline_variant=pipeline_variant,
        )
        .first()
    )
    if record is None:
        record = ModelGeneration(
            dataset_id=dataset_id,
            model_name=model_name,
            prompt_variant=prompt_variant,
            pipeline_variant=pipeline_variant,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        return record

    _collapse_generation_slot_duplicates(session, record)
    return record

# --- DB Handler ---

class DBHandler:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._generation_schema_ready: Optional[bool] = None
        self.create_schema()
    
    def create_schema(self):
        """Creates the database schema if it doesn't exist."""
        core_tables = [
            MasterMetadata.__table__,
            GroundTruthGeometry.__table__,
            StratificationData.__table__,
            CadEntity.__table__,
            GroundTruthCode.__table__,
        ]
        Base.metadata.create_all(self.engine, tables=core_tables)

        if self._has_legacy_model_generations_conflict():
            self._generation_schema_ready = False
            print(
                "Legacy wide model_generations table detected. Run "
                "utils/db/utilities/unified_generation_migration.sql before "
                "using canonical generation writes."
            )
            return

        generation_tables = [
            ModelGeneration.__table__,
            ModelGenerationCode.__table__,
            ModelGenerationArtifacts.__table__,
            ModelGenerationEvaluation.__table__,
        ]
        Base.metadata.create_all(self.engine, tables=generation_tables)
        self._generation_schema_ready = True

    def _has_legacy_model_generations_conflict(self) -> bool:
        inspector = inspect(self.engine)
        if "model_generations" not in inspector.get_table_names():
            return False
        columns = {col["name"] for col in inspector.get_columns("model_generations")}
        return "generation_id" not in columns

    def _require_canonical_generation_schema(self) -> None:
        if self._generation_schema_ready is None:
            self.create_schema()
        if not self._generation_schema_ready:
            raise RuntimeError(
                "The database still has the legacy wide model_generations table. "
                "Run utils/db/utilities/unified_generation_migration.sql to archive "
                "that table and create the canonical generation schema."
            )
        
    def get_session(self):
        return self.Session()

    # ---- Generation target compatibility helpers ----

    @staticmethod
    def _sanitize_table_name(model_name: str) -> str:
        """Convert a model name to a SQL-safe table name.
        Example: 'gpt-4o' -> 'generations_gpt_4o'
        """
        safe = _slugify_identifier(model_name)
        return f"generations_{safe}"

    @staticmethod
    def parse_generation_table_name(table_name: str) -> GenerationTarget:
        return parse_generation_table_name(table_name)

    @staticmethod
    def canonical_generation_target(
        model_name: str,
        pipeline_variant: Optional[str] = None,
    ) -> GenerationTarget:
        if pipeline_variant:
            return GenerationTarget(_slugify_identifier(model_name), pipeline_variant)
        return parse_generation_table_name(model_name)

    def get_or_create_model_table(self, model_name: str):
        """
        Compatibility shim for old callers.

        The canonical schema no longer creates per-model generations_* tables.
        This returns a logical target carrying model_name/pipeline_variant that
        save_generation_result() can use.
        """
        target = parse_generation_table_name(model_name)
        print(
            "Using canonical generation target "
            f"model_name='{target.model_name}', pipeline_variant='{target.pipeline_variant}'."
        )
        return target

    def get_or_create_master_metadata(self, dataset_id: str, folder: Optional[str] = None):
        """Ensures MasterMetadata exists for the given ID. 
        If folder is provided and prompts are missing in DB, it reads them from the folder."""
        session = self.Session()
        try:
            instance = session.query(MasterMetadata).filter_by(id=dataset_id).first()
            if not instance:
                instance = MasterMetadata(id=dataset_id)
                session.add(instance)
                
            # Populate prompts if they are empty and folder path is provided
            if folder:
                from pathlib import Path
                folder_path = Path(folder)
                
                # Expert prompt
                if not instance.expert_prompt:
                    expert_candidates = ["prompt_expert.txt", "Prompt_with_specific_measurements.txt"]
                    for name in expert_candidates:
                        fpath = folder_path / name
                        if fpath.exists():
                            instance.expert_prompt = fpath.read_text()
                            break
                            
                # Non-Expert prompt
                if not instance.non_expert_prompt:
                    non_expert_candidates = ["prompt_non_expert.txt", "prompt.txt"]
                    for name in non_expert_candidates:
                        fpath = folder_path / name
                        if fpath.exists():
                            instance.non_expert_prompt = fpath.read_text()
                            break
                            
                # Fallback: if no explicit files found but txt exists, use generic fallback mode
                if not instance.expert_prompt and not instance.non_expert_prompt:
                    found_txt = list(folder_path.glob("*.txt"))
                    if found_txt:
                        fallback_mode = "non_expert" if "Non_expert" in str(folder_path) else "expert"
                        if fallback_mode == "expert":
                            instance.expert_prompt = found_txt[0].read_text()
                        else:
                            instance.non_expert_prompt = found_txt[0].read_text()

            session.commit()
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def save_generation_result(
        self,
        dataset_id: str,
        model_name: str,
        mode: str,
        code: Optional[str],
        stl_binary: Optional[bytes],
        status: str,
        metrics: Optional[Dict[str, Any]],
        pipeline_variant: str = "baseline",
        raw_response: Optional[str] = None,
        traceback: Optional[str] = None,
        table_class=None,
    ) -> Optional[int]:
        """
        Saves generation and evaluation results to the canonical schema.

        mode: 'expert' or 'non_expert'
        table_class: legacy compatibility target from get_or_create_model_table().
        """
        self._require_canonical_generation_schema()
        if mode not in {"expert", "non_expert"}:
            raise ValueError("mode must be 'expert' or 'non_expert'.")

        target = (
            table_class
            if isinstance(table_class, GenerationTarget)
            else parse_generation_table_name(getattr(table_class, "__tablename__", model_name))
            if table_class is not None
            else self.canonical_generation_target(
                model_name,
                None if pipeline_variant == "baseline" else pipeline_variant,
            )
        )
        now = _utcnow()

        session = self.Session()
        try:
            record = _get_or_create_generation_slot(
                session,
                dataset_id=dataset_id,
                model_name=target.model_name,
                prompt_variant=mode,
                pipeline_variant=target.pipeline_variant,
                now=now,
            )
            record.status = status
            record.updated_at = now

            if record.code is None:
                record.code = ModelGenerationCode()
            record.code.generated_code = code
            if raw_response is not None:
                record.code.raw_response = raw_response
            if traceback is not None:
                record.code.traceback = traceback

            if record.artifacts is None:
                record.artifacts = ModelGenerationArtifacts()
            if stl_binary is not None:
                record.artifacts.generated_stl = stl_binary

            if record.evaluation is None:
                record.evaluation = ModelGenerationEvaluation(evaluated_at=now)
            if metrics is not None:
                record.evaluation.metrics = metrics
                record.evaluation.evaluated_at = now

            session.commit()
            print(
                f"Saved {mode} results for {dataset_id} -> "
                f"model_generations[{target.model_name}/{target.pipeline_variant}]."
            )
            return record.generation_id
            
        except Exception as e:
            session.rollback()
            print(f"DB Error saving result: {e}")
            raise
        finally:
            session.close()

    def get_ground_truth_stl(self, dataset_id: str) -> Optional[bytes]:
        """Retrieves GT STL binary."""
        session = self.Session()
        try:
            gt = session.query(GroundTruthGeometry).filter_by(id=dataset_id).first()
            if gt and gt.stl_content:
                return gt.stl_content
            return None
        finally:
            session.close()
