-- Tạo cơ sở dữ liệu
CREATE DATABASE IF NOT EXISTS FinancialManagementDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE FinancialManagementDB;

-- 1. Bảng Users (Sinh viên / Quản trị viên)
CREATE TABLE Users (
    userId INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    fullName VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100) NOT NULL UNIQUE,
    role ENUM('STUDENT', 'ADMIN') DEFAULT 'STUDENT',
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Bảng Categories (Danh mục phân loại thu/chi)
CREATE TABLE Categories (
    categoryId INT AUTO_INCREMENT PRIMARY KEY,
    userId INT NOT NULL, -- Danh mục có thể do người dùng tùy chỉnh
    categoryName VARCHAR(100) NOT NULL,
    type ENUM('INCOME', 'EXPENSE') NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES Users(userId) ON DELETE CASCADE
);

-- 3. Bảng Transactions (Giao dịch Thu/Chi)
CREATE TABLE Transactions (
    transactionId INT AUTO_INCREMENT PRIMARY KEY,
    userId INT NOT NULL,
    categoryId INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    description TEXT,
    transactionDate DATETIME NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES Users(userId) ON DELETE CASCADE,
    FOREIGN KEY (categoryId) REFERENCES Categories(categoryId) ON DELETE CASCADE
);

-- 4. Bảng Budgets (Hạn mức ngân sách tháng)
CREATE TABLE Budgets (
    budgetId INT AUTO_INCREMENT PRIMARY KEY,
    userId INT NOT NULL,
    categoryId INT NULL, -- NULL nếu là hạn mức tổng thể, có ID nếu là hạn mức theo danh mục
    amount DECIMAL(15, 2) NOT NULL,
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INT NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES Users(userId) ON DELETE CASCADE,
    FOREIGN KEY (categoryId) REFERENCES Categories(categoryId) ON DELETE CASCADE
);

-- 5. Bảng Notifications (Thông báo cảnh báo ngưỡng 80% hoặc 100%)
CREATE TABLE Notifications (
    notificationId INT AUTO_INCREMENT PRIMARY KEY,
    userId INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    isRead BOOLEAN DEFAULT FALSE,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES Users(userId) ON DELETE CASCADE
);

-- 6. Bảng SystemLogs (Nhật ký hệ thống giám sát hành động Admin/User)
CREATE TABLE SystemLogs (
    logId INT AUTO_INCREMENT PRIMARY KEY,
    userId INT NOT NULL, -- Admin hoặc User thực hiện hành động
    action VARCHAR(255) NOT NULL,
    ipAddress VARCHAR(45),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES Users(userId) ON DELETE CASCADE
);