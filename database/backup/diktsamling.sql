CREATE TABLE Diktsamling(
	Tittel CHAR(25) PRIMARY KEY NOT NULL,
	Epost CHAR(50),
	Tekst CHAR(511),
	FOREIGN KEY(Epost) REFERENCES Bruker(Epost)
);
