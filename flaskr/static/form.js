(function(){
    $(document).ready(function () {
        const MAX_FILE_SIZE = 32 * 1024 * 1024; // max acceptable file size in bytes
        const SUPPORTED_FORMATS = ['npy']; // supported file types

        var showError = function(msg) {
            $('#results').hide();
            $('#input-error').css('color', '#c22');
            $('#input-error').text("Error: " + msg);
            $('#input-error').show();
        };

        var showInfo = function(msg) {
            $('#input-error').css('color', '#222');
            $('#input-error').text(msg);
            $('#input-error').show();
        };


        $("#image-query-form").submit(function(e) {
            e.preventDefault(); // avoid to execute the actual submit of the form.

            var form = $(this);
            var url = form.attr('action');
            var fdata = new FormData(this);
            if ($("#image-query-form")[0][0].files.length == 0) {
                showError('No file specified');
                return;
            }
            var good = true;
            jQuery.each($("#image-query-form")[0][0].files, function(i, file) {
                // input pre-validation
                if (file.size > MAX_FILE_SIZE) {
                    showError('Maximum file size exceeded');
                    good = false;
                    return;
                }
                ext = file.name.substr(file.name.lastIndexOf('.') + 1);
                if (SUPPORTED_FORMATS.indexOf(ext) < 0) {
                    showError('Unsupported format, only .npy allowed');
                    good = false;
                    return;
                }
                fdata.append('file', file);
            });
            if (!good) {
                return;
            }
            fdata.append('num-results', parseInt($('#num-results')[0].value));
            fdata.append('model-id', parseInt($('#model-id')[0].value));
            showInfo("Querying, please wait...");

            var showSingleResult = function(idx) {
                var data = results[idx];
                $('#disp-dist').text(data['dist']);
                $('#disp-timestamp').text(data['timestamp']);
                $('#disp-target').text(data['target']);
                $('#disp-scannum').text(data['scannum']);
                $('#disp-band').text(data['band']);
                $('#disp-coarsechnl').text(data['coarsechnl']);
                $('#disp-prefix').text(data['prefix']);
                $('#disp-id').text(data['idx']);
                $('#disp-centerfreq').text(data['centerfreq']);
                $('#disp-img').html("<img src='" + data['wat_path'] + "' alt='waterfall'/>");
                $('#single-result').show();
                for (var i = 0; i < results.length; i++) {
                    if (i == idx) $('#result-entry-' + i).addClass('result-entry-active');
                    else $('#result-entry-' + i).removeClass('result-entry-active');
                }
            }
            $.ajax({
                type: "POST",
                url: url,
                data: fdata,
                //enctype: 'multipart/form-data',
                processData: false,
                contentType: false,
                cache: false,
                success: function(data)
                {
                    if('results' in data) {
                        results = data['results']
                        var resultsHtml = "";
                        for (var i = 0; i < results.length; i++) {
                            resultsHtml += "<div class=\"col-sm-2 result-entry\" id=\"result-entry-" + i + "\"><strong>" +
                                (i+1) + "</strong><br/>d = " + (Math.round(results[i]['dist'] * 1e7)/1e7) + "</div>";
                        }
                        var resultsList = $('#results-list');
                        console.log(results);
                        resultsList.html(resultsHtml);
                        for (var i = 0; i < results.length; i++) {
                            $('#result-entry-' + i).on('click', function(event) {
                                var i = parseInt(this.id.substr(13));
                                showSingleResult(i);
                            });
                        }

                        $('#results').show();
                        $('#input-error').hide();

                        // show first result by default
                        showSingleResult(0);
                    } else {
                        showError(data['message']);
                    }
                },
                error: function(data) {
                }
            }, 'json');
        });
    });
})()
