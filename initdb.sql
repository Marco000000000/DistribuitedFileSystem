CREATE DATABASE IF NOT EXISTS ds_filesystem;

USE ds_filesystem;

CREATE TABLE IF NOT EXISTS partitions (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    partition_name VARCHAR(20) NOT NULL,
    used_space INT NOT NULL,
    topic INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file (
    file_name VARCHAR(100) NOT NULL,
    partition_id INT UNSIGNED,
    ready BOOL ,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id,partition_id),
    FOREIGN KEY (file_id) REFERENCES partitions (id)
);

CREATE TABLE IF NOT EXISTS controller (
    id_controller INT UNSIGNED AUTO_INCREMENT KEY,
    controller_name VARCHAR (255),
    type INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS controllertopic (
    id_controller INT UNSIGNED,
    topic INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_controller,topic),
    FOREIGN KEY (id_controller) REFERENCES controller (id_controller)
);