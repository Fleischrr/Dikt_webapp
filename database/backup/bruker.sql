CREATE TABLE Bruker(
	Epost CHAR(50) PRIMARY KEY NOT NULL,
	Fornavn CHAR(30),
	Etternavn CHAR(30),
	PassordHash CHAR(65) NOT NULL,
	Salt CHAR (16) NOT NULL
);
