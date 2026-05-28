CREATE DATABASE IF NOT EXISTS tesis_gli
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE tesis_gli;

CREATE TABLE IF NOT EXISTS proyectistas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    email VARCHAR(160) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_proyectista_nombre (nombre_completo)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS proyectos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyectista_id INT NOT NULL,
    nombre VARCHAR(160) NOT NULL,
    descripcion TEXT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proyectista_id) REFERENCES proyectistas(id),
    UNIQUE KEY uq_proyecto_por_proyectista (proyectista_id, nombre)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS simulaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    creado_en VARCHAR(40) NOT NULL,
    entradas_json JSON NOT NULL,
    metricas_json JSON NOT NULL,
    puntos_json JSON NOT NULL,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id),
    INDEX idx_proyecto_id (proyecto_id),
    INDEX idx_creado_en (creado_en)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
