from __future__ import annotations

import sqlite3
from pathlib import Path

from app.catalogue_models import CaseServiceLink, ServiceCatalogueEntry, ServiceDependency


class SQLiteCatalogueRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS catalogue_services (service_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS catalogue_dependencies (dependency_id TEXT PRIMARY KEY, source_service_id TEXT NOT NULL, target_service_id TEXT NOT NULL, payload_json TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS catalogue_case_links (link_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, service_id TEXT NOT NULL, payload_json TEXT NOT NULL)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_catalogue_dependency_source ON catalogue_dependencies(source_service_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_catalogue_dependency_target ON catalogue_dependencies(target_service_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_catalogue_case_link_case ON catalogue_case_links(case_id)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_case_link_unique ON catalogue_case_links(case_id, service_id)")

    def save_service(self, service: ServiceCatalogueEntry) -> ServiceCatalogueEntry:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO catalogue_services(service_id, payload_json) VALUES (?, ?) ON CONFLICT(service_id) DO UPDATE SET payload_json=excluded.payload_json",
                (service.service_id, service.model_dump_json()),
            )
        return service

    def get_service(self, service_id: str) -> ServiceCatalogueEntry | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM catalogue_services WHERE service_id = ?", (service_id,)).fetchone()
        return None if row is None else ServiceCatalogueEntry.model_validate_json(row["payload_json"])

    def list_services(self, *, active_only: bool = True) -> list[ServiceCatalogueEntry]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM catalogue_services ORDER BY service_id").fetchall()
        services = [ServiceCatalogueEntry.model_validate_json(row["payload_json"]) for row in rows]
        return [service for service in services if service.active] if active_only else services

    def save_dependency(self, dependency: ServiceDependency) -> ServiceDependency:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO catalogue_dependencies(dependency_id, source_service_id, target_service_id, payload_json) VALUES (?, ?, ?, ?) ON CONFLICT(dependency_id) DO UPDATE SET source_service_id=excluded.source_service_id, target_service_id=excluded.target_service_id, payload_json=excluded.payload_json",
                (dependency.dependency_id, dependency.source_service_id, dependency.target_service_id, dependency.model_dump_json()),
            )
        return dependency

    def list_dependencies_for_service(self, service_id: str) -> list[ServiceDependency]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM catalogue_dependencies WHERE source_service_id = ? OR target_service_id = ? ORDER BY dependency_id",
                (service_id, service_id),
            ).fetchall()
        return [ServiceDependency.model_validate_json(row["payload_json"]) for row in rows]

    def save_case_link(self, link: CaseServiceLink) -> CaseServiceLink:
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO catalogue_case_links(link_id, case_id, service_id, payload_json) VALUES (?, ?, ?, ?)",
                    (link.link_id, link.case_id, link.service_id, link.model_dump_json()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("The case is already linked to this catalogue service.") from exc
        return link

    def list_case_links(self, case_id: str) -> list[CaseServiceLink]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM catalogue_case_links WHERE case_id = ? ORDER BY link_id",
                (case_id,),
            ).fetchall()
        return [CaseServiceLink.model_validate_json(row["payload_json"]) for row in rows]
