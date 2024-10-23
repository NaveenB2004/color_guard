<html lang="en">
<head>
    <link rel="icon" type="image/png" href="img/AppLogo.png">
    <link rel="stylesheet" href="bootstrap/css/bootstrap.min.css">
    <title>Annotation results</title>
    <style>
        .color-block {
            display: inline-block;
            width: 50px;
            height: 50px;
            margin-right: 10px;
            border: 1px solid #000;
        }

        .color-container {
            margin-bottom: 20px;
        }

        .element-container {
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }

        .element-container img {
            width: 100px;
            height: auto;
            margin-right: 10px;
        }

        .element-details {
            display: inline-block;
            vertical-align: top;
        }

        .annotated-image {
            max-width: 80%;
            height: auto;
            margin-bottom: 30px;
            display: block;
        }
    </style>
</head>
<body class="bg-light">

<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-11">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h2 class="card-title text-center mb-3">Annotation Results</h2>
                    <?php
                    function delete_all($folder_path)
                    {
                        $files = glob($folder_path . '/*');
                        foreach ($files as $file) {
                            if (is_dir($file)) {
                                delete_all($file);
                                rmdir($file);
                            } else {
                                unlink($file);
                            }
                        }
                    }

                    if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_FILES['screenshot'])) {
                        delete_all("uploads");
                        $target_dir = "uploads/";
                        $target_file = $target_dir . basename($_FILES["screenshot"]["name"]);

                        if (move_uploaded_file($_FILES["screenshot"]["tmp_name"], $target_file)) {
                            $python_path = 'C:\\Users\\Anupama\\AppData\\Local\\Programs\\Python\\Python312\\python.exe';
                            $escaped_target_file = escapeshellarg($target_file);

                            // Run the Python annotation script to extract primary and secondary colors
                            $command = escapeshellcmd("$python_path annotate_image.py $escaped_target_file");
                            exec($command . ' 2>&1', $output, $result_code);

                            if ($result_code === 0) {
                                $primary_color = trim($output[0] ?? "#000000");
                                $secondary_color = trim($output[1] ?? "#FFFFFF");

                                // Display primary and secondary colors
                                echo "<h4>Primary and Secondary Colors</h4>";
                                echo "<div class='row text-center mt-3'>";
                                echo "  <div class='col-md-6'>";
                                echo "      <div class='p-3' style='background-color: " . htmlspecialchars($primary_color) . "; height: 100px; border-radius: 10px;'></div>";
                                echo "      <p class='mt-2'><strong>Primary Color:</strong> " . htmlspecialchars($primary_color) . "</p>";
                                echo "  </div>";
                                echo "  <div class='col-md-6'>";
                                echo "      <div class='p-3' style='background-color: " . htmlspecialchars($secondary_color) . "; height: 100px; border-radius: 10px;'></div>";
                                echo "      <p class='mt-2'><strong>Secondary Color:</strong> " . htmlspecialchars($secondary_color) . "</p>";
                                echo "  </div>";
                                echo "</div>";

                                // Display the whole annotated image
                                echo "<div class='container mt-5'>";
                                echo "<div class='row'>";
                                echo "<div class='col-md-5'>";
                                echo "<h4>Annotated Image</h4>";
                                echo "<img src='uploads/annotated_image.jpg' alt='Uploaded Screenshot' style='max-width: 100%; height: auto;' class='annotated-image border'>";
                                echo "</div>";

                                // Run the generate_tips.py script with extracted colors
                                $generate_tips_command = escapeshellcmd("$python_path generate_tips.py uploads/element_data.json $primary_color $secondary_color");
                                exec($generate_tips_command, $tips_output, $tips_status);

                                if ($tips_status === 0) {
                                    $tips_json = file_get_contents('uploads/ui_tips.json');
                                    $tips_data = json_decode($tips_json, true);

                                    echo "<div class='col-md-7'>";
                                    echo "<h4>Annotated Elements with Violated Guidelines and Improvement Tips</h4>";
                                    foreach ($tips_data as $index => $tip) {
                                        $cropped_image_path = "uploads/cropped_element_" . ($index + 1) . ".jpg";
                                        echo "<div class='element-container'>";
                                        echo "<img src='" . htmlspecialchars($cropped_image_path) . "' alt='Element'>";
                                        echo "<div class='element-details'>";
                                        echo "<p><strong>Element:</strong> " . htmlspecialchars($tip['element_type']) . "</p>";
                                        echo "<p><strong>Color:</strong> " . htmlspecialchars($tip['color']) . "</p>";

                                        // Display violated guideline, if any
                                        if (isset($tip['violated_guideline']) && $tip['violated_guideline']) {
                                            echo "<p><strong>Violated Guideline:</strong> " . htmlspecialchars($tip['violated_guideline']) . "</p>";
                                        }

                                        // Display the tip
                                        echo "<p><strong>Tip:</strong> " . htmlspecialchars($tip['tip']) . "</p>";
                                        echo "</div>";
                                        echo "</div>";
                                    }
                                    echo "</div>";
                                    echo "</div>";
                                    echo "</div>";
                                } else {
                                    echo "<p>Error generating UI improvement tips.</p>";
                                }
                            } else {
                                echo "<p>Failed to annotate the image. Please try again.</p>";
                            }
                        } else {
                            echo "<p>Error uploading the file.</p>";
                        }
                    } else {
                        echo "<p>No file uploaded. Please try again.</p>";
                    }
                    ?>
                    <div class="mt-4 text-center">
                        <a href="home.html" class="btn btn-primary">Go Back</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
