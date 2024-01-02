CREATE DATABASE IF NOT EXISTS ds_filesystem;

USE ds_filesystem;

CREATE TABLE IF NOT EXISTS partitions (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    partition_name VARCHAR(20) NOT NULL,
    used_space INT NOT NULL,
    topic INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS files (
	file_id INT UNSIGNED AUTO_INCREMENT,
    file_name VARCHAR(100) NOT NULL,
    partition_id INT UNSIGNED,
    ready BOOL ,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id,partition_id),
    FOREIGN KEY (file_id) REFERENCES partitions (id)
);

CREATE TABLE IF NOT EXISTS controller (
    id_controller INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    controller_name VARCHAR (255) UNIQUE,
    cType VARCHAR(20)  NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS controllertopic (
    id_controller INT UNSIGNED,
    topic INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_controller,topic),
    FOREIGN KEY (id_controller) REFERENCES controller (id_controller)
);


-- Creazione utente file_manager
CREATE USER IF NOT EXISTS 'file_manager'@'localhost' IDENTIFIED BY 'file';

GRANT SELECT ON ds_filesystem.files TO file_manager@uploadcontroller; -- Permesso di lettura
GRANT INSERT ON ds_filesystem.files TO file_manager@uploadcontroller; -- Permesso di inserimento di record all'interno della tabella
GRANT UPDATE ON ds_filesystem.files TO file_manager@uploadcontroller; -- Permesso di modifica dei record presenti nella tabella
GRANT DELETE ON ds_filesystem.files TO file_manager@uploadcontroller; -- Permesso di eliminazione dei record dalla tabella

FLUSH PRIVILEGES;