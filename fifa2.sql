CREATE DATABASE fifa;
USE fifa;

CREATE TABLE User (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE Team (
    team_id INT PRIMARY KEY AUTO_INCREMENT,
    team_name VARCHAR(255) NOT NULL,
    formation VARCHAR(100),
    user_id INT,
    avg_ovr int,
    FOREIGN KEY (user_id) REFERENCES User(user_id) on delete cascade on update cascade
);

CREATE TABLE club (
    item_id INT,
    team_id INT,
    PRIMARY KEY (team_id, item_id),
    FOREIGN KEY (team_id) REFERENCES Team(team_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (item_id) REFERENCES Item(item_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


CREATE TABLE Player (
    player_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    nationality VARCHAR(100),
    position VARCHAR(100),
    imagedir varchar(255)
    
);

CREATE TABLE Item (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    ovr INT,
    player_id INT,
    FOREIGN KEY (player_id) REFERENCES Player(player_id)
);

CREATE TABLE Matches (
    match_id INT PRIMARY KEY AUTO_INCREMENT,
    home_team_id INT,
    away_team_id INT,
    FOREIGN KEY (home_team_id) REFERENCES Team(team_id) on delete cascade on update cascade,
    FOREIGN KEY (away_team_id) REFERENCES Team(team_id) on delete cascade on update cascade,
);

delimiter //
create trigger update_team_ovr
after insert  on club
for each row
begin
	update team
	set avg_ovr=(
		select avg(i.ovr)
		from Item I
		join Club c on i.item_id=c.item_id
		where c.team_id=new.team_id
	)
    where team_id=NEW.team_id;
    
end//
delimiter;

delimiter //
create trigger update_team_ovr_after_delete
after delete on club
for each row
begin
	update team
	set avg_ovr=(
		select avg(i.ovr)
		from Item i join Club c on i.item_id=c.item_id
		where c.team_id=old.team_id
	)
    where team_id=old.team_id;
    
end//
delimiter ;


delimiter //
create trigger update_team_ovr_after_update_item
after update on item
for each row
begin
	update team
	set avg_ovr=(
		select avg(i.ovr) from item i
        join club c
        on i.item_id=c.item_id
        where c.team_id=team.team_id
    )
    where team_id in 
		(SELECT c.team_id
        FROM Club c
        WHERE c.item_id = NEW.item_id
        );
end//
delimiter ;

DELIMITER //
CREATE PROCEDURE AddPlayer(
    IN p_name VARCHAR(255),
    IN p_nationality VARCHAR(100),
    IN p_position VARCHAR(100),
    IN p_imagedir varchar(255),
    IN p_ovr INT
)
BEGIN
    DECLARE new_player_id INT;
    INSERT INTO Player(name, nationality, position, imagedir)
    VALUES (p_name, p_nationality, p_position, p_imagedir);
    SET new_player_id = LAST_INSERT_ID();
    insert into item(ovr,player_id) values(p_ovr,new_player_id);
END //
DELIMITER ;


DELIMITER //
CREATE PROCEDURE UpdatePlayer(
    IN p_player_id INT,
    IN p_name VARCHAR(255),
    IN p_nationality VARCHAR(100),
    IN p_position VARCHAR(100),
    IN p_imagedir VARCHAR(255),
    IN p_ovr INT
)
BEGIN
    UPDATE Player
    SET name = p_name,
        nationality = p_nationality,
        position = p_position,
        imagedir = p_imagedir
    WHERE player_id = p_player_id;
    UPDATE Item
    SET ovr = p_ovr
    WHERE player_id = p_player_id;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE DeletePlayer(
    IN p_player_id INT
)
BEGIN
    DELETE FROM Item
    WHERE player_id = p_player_id;

    DELETE FROM Player
    WHERE player_id = p_player_id;
END //
DELIMITER ;

CREATE VIEW TeamPlayers AS
SELECT 
    t.team_id,
    t.team_name,
    p.player_id,
    p.name AS player_name,
    i.ovr
FROM Team t
JOIN Club c ON t.team_id = c.team_id
JOIN Item i ON c.item_id = i.item_id
JOIN Player p ON i.player_id = p.player_id;

